"""Fixture identity safety and IAP fail-closed behaviour (auth test 12, fixture side)."""

import pytest
from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.auth import FIXTURE_HEADER, IAP_HEADER, PERMISSIONS, Action, allowed
from control_plane.contracts import Role
from control_plane.settings import IdentityMode, Settings, UnsafeBindError, assert_safe_bind
from control_plane.store import MemoryStore
from tests.conftest import make_client


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "::"])  # noqa: S104
def test_fixture_identity_refuses_non_local_bind(host: str) -> None:
    with pytest.raises(UnsafeBindError):
        assert_safe_bind(Settings(_env_file=None, bind_host=host))


def test_fixture_app_refuses_to_start_on_non_local_bind() -> None:
    app = create_app(Settings(_env_file=None, bind_host="0.0.0.0"), MemoryStore())  # noqa: S104
    with pytest.raises(UnsafeBindError), TestClient(app):
        pass


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_fixture_identity_allows_local_bind(host: str) -> None:
    assert_safe_bind(Settings(_env_file=None, bind_host=host))


def test_iap_mode_may_bind_anywhere() -> None:
    assert_safe_bind(
        Settings(_env_file=None, identity_mode=IdentityMode.IAP, bind_host="0.0.0.0")  # noqa: S104
    )


def test_missing_fixture_header_rejected() -> None:
    assert make_client().get("/api/me").status_code == 401


def test_unknown_fixture_user_rejected() -> None:
    r = make_client().get("/api/me", headers={FIXTURE_HEADER: "nobody@example.com"})
    assert r.status_code == 401


def test_known_fixture_user_gets_role_from_store() -> None:
    r = make_client().get("/api/me", headers={FIXTURE_HEADER: "Admin@Example.com"})
    assert r.status_code == 200
    assert r.json() == {"email": "admin@example.com", "role": "governance_admin"}


def test_non_loopback_client_rejected_in_fixture_mode() -> None:
    store = MemoryStore()
    client = make_client(store=store)
    remote = TestClient(client.app, client=("10.0.0.7", 50000))
    r = remote.get("/api/me", headers={FIXTURE_HEADER: "admin@example.com"})
    assert r.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [{}, {IAP_HEADER: "forged.jwt.value"}, {FIXTURE_HEADER: "admin@example.com"}],
)
def test_iap_mode_fails_closed(headers: dict[str, str]) -> None:
    client = make_client(Settings(_env_file=None, identity_mode=IdentityMode.IAP))
    assert client.get("/api/me", headers=headers).status_code == 401


def test_executive_viewer_reads_portfolio_only() -> None:
    client = make_client()
    h = {FIXTURE_HEADER: "exec@example.com"}
    assert client.get("/api/portfolio/summary", headers=h).status_code == 200
    assert client.get("/api/apps/support-triage", headers=h).status_code == 403
    assert client.get("/api/incidents", headers=h).status_code == 403


def test_every_role_has_permissions_and_only_admin_manages_roles() -> None:
    assert set(PERMISSIONS) == set(Role)
    assert [r for r in Role if allowed(r, Action.MANAGE_ROLES)] == [Role.GOVERNANCE_ADMIN]
    assert not any(allowed(Role.EXECUTIVE_VIEWER, a) for a in Action if "read" not in a)
