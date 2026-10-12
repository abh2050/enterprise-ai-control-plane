"""Identity and authorization.

The role always comes from the ``users`` collection, never from the request or a model.

- Fixture mode reads the caller's email from ``X-Fixture-User``. Because a header is
  trivially forgeable, fixture mode only serves loopback clients and refuses to bind
  to any non-local interface (see ``settings.assert_safe_bind``).
- IAP mode verifies ``x-goog-iap-jwt-assertion`` on every request (control_plane.iap):
  signature, issuer, audience, and expiry. Missing or invalid assertions are rejected.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from control_plane.contracts import Me, Role
from control_plane.settings import LOCAL_HOSTS, IdentityMode, Settings
from control_plane.store import Store

FIXTURE_HEADER = "X-Fixture-User"
IAP_HEADER = "X-Goog-IAP-JWT-Assertion"


class Action(StrEnum):
    READ_PORTFOLIO = "read_portfolio"
    READ_FLOW = "read_flow"
    READ_REPORTS = "read_reports"
    READ_APP_DETAIL = "read_app_detail"
    READ_REVIEWS = "read_reviews"
    READ_INCIDENTS = "read_incidents"
    PROPOSE_APP = "propose_app"
    ADVANCE_OWN_APP = "advance_own_app"
    CREATE_CONFIG = "create_config"
    REQUEST_EVALUATION = "request_evaluation"
    PROPOSE_RELEASE = "propose_release"
    APPROVE_GATE = "approve_gate"
    APPROVE_CASE = "approve_case"
    PUBLISH_EXTERNAL_APP = "publish_external_app"
    DECIDE_RELEASE = "decide_release"
    PAUSE_APP = "pause_app"
    ROLLBACK = "rollback"
    MANAGE_ROLES = "manage_roles"
    EXPORT_PORTFOLIO = "export_portfolio"


_EXECUTIVE = {Action.READ_PORTFOLIO, Action.READ_FLOW, Action.READ_REPORTS}
_READ_ALL = _EXECUTIVE | {Action.READ_APP_DETAIL, Action.READ_REVIEWS, Action.READ_INCIDENTS}

PERMISSIONS: dict[Role, frozenset[Action]] = {
    Role.EXECUTIVE_VIEWER: frozenset(_EXECUTIVE),
    Role.APP_OWNER: frozenset(
        _READ_ALL
        | {
            Action.PROPOSE_APP,
            Action.ADVANCE_OWN_APP,
            Action.CREATE_CONFIG,
            Action.REQUEST_EVALUATION,
            Action.PROPOSE_RELEASE,
        }
    ),
    Role.REVIEWER: frozenset(_READ_ALL | {Action.APPROVE_GATE, Action.APPROVE_CASE}),
    Role.GOVERNANCE_ADMIN: frozenset(
        _READ_ALL
        | {
            Action.APPROVE_GATE,
            Action.PUBLISH_EXTERNAL_APP,
            Action.DECIDE_RELEASE,
            Action.PAUSE_APP,
            Action.ROLLBACK,
            Action.MANAGE_ROLES,
            Action.EXPORT_PORTFOLIO,
        }
    ),
}


def allowed(role: Role, action: Action) -> bool:
    return action in PERMISSIONS[role]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def resolve_user(request: Request, settings: Settings, store: Store) -> Me:
    if settings.identity_mode is IdentityMode.IAP:
        from control_plane.iap import IapError, verify

        cache = request.app.state.iap_keys
        try:
            claims = verify(request.headers.get(IAP_HEADER), settings.iap_audience, cache)
        except IapError as exc:
            raise _unauthorized(str(exc)) from exc
        iap_email = str(claims["email"]).lower()
        user = store.get("users", iap_email)
        if user is None or not user.get("active", False):
            raise _unauthorized("unknown or inactive user")
        return Me(email=user["email"], role=Role(user["role"]))

    client_host = request.client.host if request.client else None
    if client_host not in LOCAL_HOSTS:
        raise _unauthorized("fixture identity only serves loopback clients")

    fixture_email = request.headers.get(FIXTURE_HEADER)
    if not fixture_email:
        raise _unauthorized(f"missing {FIXTURE_HEADER} header")
    user = store.get("users", fixture_email.strip().lower())
    if user is None or not user.get("active", False):
        raise _unauthorized("unknown or inactive user")
    return Me(email=user["email"], role=Role(user["role"]))


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_store(request: Request) -> Store:
    store: Store = request.app.state.store
    return store


def current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    store: Annotated[Store, Depends(get_store)],
) -> Me:
    return resolve_user(request, settings, store)


def require(action: Action) -> Callable[[Me], Me]:
    """Dependency factory: ``user: Annotated[Me, Depends(require(Action.X))]``."""

    def _check(user: Annotated[Me, Depends(current_user)]) -> Me:
        if not allowed(user.role, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role {user.role} may not {action}",
            )
        return user

    return _check
