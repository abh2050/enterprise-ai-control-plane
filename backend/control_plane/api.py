"""FastAPI application: JSON API under /api and the built console at /.

Every write re-scores Governance Assist, so Portfolio, Pipeline, and Flow read the same
state after a mutation. Registry errors map to HTTP codes: 403 forbidden, 404 not
found, 409 stale version (with the current record), 422 missing requirement.
"""

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from control_plane import assist, notes, portfolio, registry
from control_plane.auth import Action, allowed, current_user, get_store, require
from control_plane.contracts import DataMode, Me, ModeInfo, Role
from control_plane.fixtures import seed_registry
from control_plane.settings import (
    IdentityMode,
    ProviderMode,
    Settings,
    StoreBackend,
    assert_safe_bind,
    get_settings,
)
from control_plane.store import Store, build_store

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
EXPERIMENT_SUMMARY = ROOT / "artifacts" / "experiment_summary.json"
PRODUCT_EVENTS = {
    "portfolio_viewed",
    "metric_drilldown_opened",
    "assist_opened",
    "assist_action_completed",
    "app_drag_started",
    "app_stage_change_completed",
    "app_stage_change_failed",
    "flow_filter_changed",
    "app_drawer_opened",
    "note_created",
    "theme_changed",
}


# Request bodies


class MoveBody(BaseModel):
    to_stage: str
    expected_version: int
    reason: str | None = None
    source: str = Field(default="api", pattern="^(drag|keyboard|menu|api)$")


class GateBody(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    reason: str


class DismissBody(BaseModel):
    code: str
    reason: str


class MarkSafeBody(BaseModel):
    note: str


class ScheduleBody(BaseModel):
    review_at: datetime
    expected_version: int
    note: str = ""


class NoteBody(BaseModel):
    text: str
    idempotency_key: str


class NoteEditBody(BaseModel):
    text: str


class NoteDeleteBody(BaseModel):
    reason: str


class RoleBody(BaseModel):
    role: Role
    active: bool = True
    security_reviewer: bool = False


class ProductEvent(BaseModel):
    """Analytics event: never carries note text or personal data."""

    model_config = {"extra": "forbid"}
    event: str
    app_id: str | None = None
    source_view: str = Field(max_length=40)


def create_app(settings: Settings | None = None, store: Store | None = None) -> FastAPI:
    settings = settings or get_settings()

    def now() -> datetime:
        return settings.fixed_now or datetime.now(UTC)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        assert_safe_bind(settings)
        if (
            settings.store_backend is StoreBackend.MEMORY
            and settings.identity_mode is IdentityMode.FIXTURE
            and not app.state.store.list("apps")
        ):
            seed_registry(app.state.store, now())
        yield

    app = FastAPI(title="Enterprise AI Control Plane", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store if store is not None else build_store(settings)
    StoreDep = Annotated[Store, Depends(get_store)]

    @app.exception_handler(registry.RegistryError)
    async def registry_error(_: Request, exc: registry.RegistryError) -> JSONResponse:
        body: dict[str, Any] = {"detail": str(exc)}
        if isinstance(exc, registry.RequirementMissingError):
            body["code"] = exc.code
        if isinstance(exc, registry.VersionConflictError):
            body["current"] = exc.current
        return JSONResponse(status_code=exc.status, content=body)

    def actor(user: Me, store: Store) -> registry.Actor:
        record = store.get("users", user.email) or {}
        return registry.Actor(user.email, user.role, bool(record.get("security_reviewer")))

    def rescore(store: Store) -> None:
        assist.score_all(store, now())

    def ctx(store: Store, platform: str | None, range_days: int) -> portfolio.Context:
        return portfolio.Context(store, now(), portfolio.Filters(platform or None, range_days))

    # Shell

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/mode")
    def mode(store: StoreDep) -> ModeInfo:
        from control_plane.contracts import DatasetLabel

        present = {d.get("provenance") for d in store.list("apps")}
        labels = [label for label in DatasetLabel if label.value in present]
        data_mode = (
            DataMode.LIVE
            if (
                settings.identity_mode is IdentityMode.IAP
                and settings.provider_mode is not ProviderMode.FIXTURE
            )
            else DataMode.FIXTURE
        )
        return ModeInfo(
            data_mode=data_mode,
            identity_mode=settings.identity_mode.value,
            provider_mode=settings.provider_mode.value,
            store_backend=settings.store_backend.value,
            dataset_labels=labels,
        )

    @app.get("/api/me")
    def me(user: Annotated[Me, Depends(current_user)], store: StoreDep) -> dict[str, Any]:
        return {
            "email": user.email,
            "role": user.role.value,
            "permissions": sorted(a.value for a in Action if allowed(user.role, a)),
            "security_reviewer": bool(
                (store.get("users", user.email) or {}).get("security_reviewer")
            ),
        }

    @app.get("/api/fixture/users")
    def fixture_users(store: StoreDep) -> list[dict[str, Any]]:
        if settings.identity_mode is not IdentityMode.FIXTURE:
            raise HTTPException(status_code=404)
        fixtures = {
            "owner@example.com",
            "owner2@example.com",
            "reviewer@example.com",
            "security@example.com",
            "admin@example.com",
            "exec@example.com",
        }
        return [
            {"email": u["email"], "role": u["role"]}
            for u in store.list("users")
            if u["email"] in fixtures
        ]

    # Portfolio

    ReadPortfolio = Annotated[Me, Depends(require(Action.READ_PORTFOLIO))]

    @app.get("/api/portfolio")
    def get_portfolio(
        _: ReadPortfolio,
        store: StoreDep,
        platform: str | None = None,
        range: int = Query(90, ge=7, le=180),
    ) -> dict[str, Any]:  # noqa: A002
        return portfolio.portfolio(ctx(store, platform, range))

    @app.get("/api/portfolio/spend")
    def spend(_: ReadPortfolio, store: StoreDep, platform: str | None = None) -> list[Any]:
        return portfolio.spend_breakdown(ctx(store, platform, 90))

    @app.get("/api/apps")
    def list_apps(
        _: ReadPortfolio,
        store: StoreDep,
        platform: str | None = None,
        q: str | None = None,
        stage: str | None = None,
        risk: str | None = None,
        owner: str | None = None,
        business_unit: str | None = None,
        health: str | None = None,
        spend_min: float | None = None,
        spend_max: float | None = None,
        sort: str = "recent",
    ) -> list[dict[str, Any]]:
        return portfolio.catalog(
            ctx(store, platform, 90),
            q=q,
            stage=stage,
            risk=risk,
            owner=owner,
            business_unit=business_unit,
            health_status=health,
            spend_min=spend_min,
            spend_max=spend_max,
            sort=sort,
        )

    @app.get("/api/export/catalog.csv")
    def export_csv(
        user: Annotated[Me, Depends(require(Action.EXPORT_PORTFOLIO))],
        store: StoreDep,
        platform: str | None = None,
        stage: str | None = None,
        q: str | None = None,
        health: str | None = None,
    ) -> Response:
        cards = portfolio.catalog(ctx(store, platform, 90), q=q, stage=stage, health_status=health)
        return Response(
            portfolio.catalog_csv(cards),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=catalog.csv"},
        )

    @app.get("/api/flow")
    def get_flow(
        _: Annotated[Me, Depends(require(Action.READ_FLOW))],
        store: StoreDep,
        platform: str | None = None,
        range: int = Query(90, ge=7, le=180),
    ) -> dict[str, Any]:  # noqa: A002
        return portfolio.flow(ctx(store, platform, range))

    # App detail and moves

    ReadDetail = Annotated[Me, Depends(require(Action.READ_APP_DETAIL))]

    def load_app(store: Store, app_id: str) -> dict[str, Any]:
        app_doc = store.get("apps", app_id)
        if app_doc is None:
            raise HTTPException(status_code=404, detail="app not found")
        return app_doc

    @app.get("/api/apps/{app_id}")
    def get_app(app_id: str, user: ReadDetail, store: StoreDep) -> dict[str, Any]:
        app_doc = load_app(store, app_id)
        c = ctx(store, None, 90)
        events = sorted(store.list(f"apps/{app_id}/events"), key=lambda e: e["created_at"])
        incidents = [i for i in store.list("incidents") if i["app_id"] == app_id]
        moves = {
            s: registry.check_move(app_doc, s, actor(user, store), "reason", now())
            for s in registry.load_lifecycle().stages
        }
        return {
            "app": app_doc,
            "card": portfolio.card(app_doc, c),
            "events": events,
            "incidents": incidents,
            "assist": store.get("assist_scores", app_id),
            "notes": notes.list_notes(store, app_id),
            "allowed_moves": {
                s: {
                    "allowed": m.allowed,
                    "code": m.code,
                    "message": m.message,
                    "needs_reason": bool(m.transition and "reason" in m.transition["requires"]),
                }
                for s, m in moves.items()
            },
            "external": app_doc["platform"] != "managed",
        }

    @app.post("/api/apps/{app_id}/move")
    def move_app(
        app_id: str, body: MoveBody, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> dict[str, Any]:
        if user.role is Role.EXECUTIVE_VIEWER:
            raise HTTPException(status_code=403, detail="read only")
        updated, event = registry.move(
            store,
            app_id,
            body.to_stage,
            actor(user, store),
            body.expected_version,
            body.reason,
            source=body.source,
            now=now(),
        )
        rescore(store)
        return {"app": updated, "event": event}

    @app.post("/api/apps/{app_id}/gates/{gate}")
    def decide_gate(
        app_id: str,
        gate: str,
        body: GateBody,
        user: Annotated[Me, Depends(current_user)],
        store: StoreDep,
    ) -> dict[str, Any]:
        if not allowed(user.role, Action.APPROVE_GATE):
            raise HTTPException(status_code=403, detail="Your role cannot decide gates")
        out = registry.approve_gate(
            store, app_id, gate, actor(user, store), body.decision, body.reason, now()
        )
        rescore(store)
        return out

    # Governance Assist

    @app.get("/api/assist")
    def get_assist(_: ReadPortfolio, store: StoreDep) -> dict[str, Any]:
        scores = sorted(store.list("assist_scores"), key=lambda s: (-s["score"], s["app_id"]))
        apps = {a["app_id"]: a for a in store.list("apps")}
        c = ctx(store, None, 90)
        rows = []
        for s in scores:
            a = apps.get(s["app_id"])
            if a is None or a["stage"] == "retired":
                continue
            card = portfolio.card(a, c)
            rows.append(
                {
                    **s,
                    "name": a["name"],
                    "stage": a["stage"],
                    "version": a.get("version", 1),
                    "spend": card["monthly_spend_usd"],
                    "value": card["estimated_value_usd"],
                }
            )
        rows.sort(key=lambda r: (-r["score"], -(r["spend"].value or 0)))
        lc = registry.load_lifecycle()
        return {
            "threshold": lc.raw["assist"]["threshold"],
            "rows": rows,
            "rules": lc.raw["assist"]["signals"],
            "scored_at": max((s["scored_at"] for s in scores), default=None),
        }

    @app.post("/api/assist/{app_id}/dismiss")
    def assist_dismiss(
        app_id: str, body: DismissBody, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> dict[str, Any]:
        if user.role is Role.EXECUTIVE_VIEWER:
            raise HTTPException(status_code=403, detail="read only")
        out = assist.dismiss(store, app_id, body.code, user.email, body.reason, now())
        rescore(store)
        return out

    @app.post("/api/assist/{app_id}/mark-safe")
    def assist_mark_safe(
        app_id: str, body: MarkSafeBody, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> dict[str, Any]:
        out = assist.mark_safe(store, app_id, user.email, user.role.value, body.note, now())
        rescore(store)
        return out

    @app.post("/api/assist/{app_id}/schedule-review")
    def assist_schedule(
        app_id: str, body: ScheduleBody, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> dict[str, Any]:
        if user.role is Role.EXECUTIVE_VIEWER:
            raise HTTPException(status_code=403, detail="read only")
        out = assist.schedule_review(
            store, app_id, user.email, body.review_at, body.expected_version, body.note, now()
        )
        rescore(store)
        return out

    # Notes

    @app.post("/api/apps/{app_id}/notes")
    def add_note(
        app_id: str, body: NoteBody, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> dict[str, Any]:
        if user.role is Role.EXECUTIVE_VIEWER:
            raise HTTPException(status_code=403, detail="read only")
        note, created = notes.create_note(
            store, app_id, user.email, body.text, body.idempotency_key, now()
        )
        return {"note": note, "created": created}

    @app.patch("/api/notes/{note_id}")
    def edit_note(
        note_id: str,
        body: NoteEditBody,
        user: Annotated[Me, Depends(current_user)],
        store: StoreDep,
    ) -> dict[str, Any]:
        return notes.edit_note(store, note_id, user.email, body.text, now())

    @app.post("/api/notes/{note_id}/delete")
    def delete_note(
        note_id: str,
        body: NoteDeleteBody,
        user: Annotated[Me, Depends(current_user)],
        store: StoreDep,
    ) -> dict[str, Any]:
        return notes.delete_note(store, note_id, user.email, user.role.value, body.reason, now())

    # Reviews and incidents

    @app.get("/api/reviews/pending")
    def pending_reviews(
        user: Annotated[Me, Depends(require(Action.READ_REVIEWS))], store: StoreDep
    ) -> dict[str, Any]:
        lc = registry.load_lifecycle()
        me_actor = actor(user, store)
        items = []
        for a in store.list("apps"):
            for gate in registry.pending_gate_items(a, lc):
                approvers = lc.raw["gate_approvers"][gate]
                own = user.email in (a.get("submitted_by"), a.get("owner"))
                can = me_actor.role.value in approvers or (
                    "security_reviewer" in approvers and me_actor.security_reviewer
                )
                items.append(
                    {
                        "app_id": a["app_id"],
                        "name": a["name"],
                        "gate": gate,
                        "risk_tier": a["risk_tier"],
                        "submitted_by": a.get("submitted_by"),
                        "owner": a.get("owner"),
                        "version": a.get("version", 1),
                        "evidence": {
                            "business_problem": a["business_problem"],
                            "business_case": a.get("business_case"),
                            "platform": a["platform"],
                        },
                        "rubric": lc.raw["review_rubric"].get(gate, []),
                        "can_decide": can and not own,
                        "blocked_reason": (
                            "A different person must approve: you submitted or own this app"
                        )
                        if own
                        else (None if can else f"The {gate} gate needs {', '.join(approvers)}"),
                    }
                )
        return {"gates": items, "cases": []}  # routed cases arrive with shadow replay (M5)

    @app.get("/api/incidents")
    def incidents(
        _: Annotated[Me, Depends(require(Action.READ_INCIDENTS))], store: StoreDep
    ) -> list[dict[str, Any]]:
        return sorted(store.list("incidents"), key=lambda i: i["opened_at"], reverse=True)

    # Support Triage evidence (App Detail tabs)

    @app.get("/api/apps/{app_id}/evidence")
    def evidence(app_id: str, _: ReadDetail) -> dict[str, Any]:
        if app_id != "support-triage" or not EXPERIMENT_SUMMARY.exists():
            return {"available": False}
        data: dict[str, Any] = json.loads(EXPERIMENT_SUMMARY.read_text())
        return {"available": True, **data}

    # Settings

    @app.get("/api/settings/users")
    def users(
        _: Annotated[Me, Depends(require(Action.MANAGE_ROLES))], store: StoreDep
    ) -> list[dict[str, Any]]:
        return sorted(store.list("users"), key=lambda u: u["email"])

    @app.post("/api/settings/users/{email}")
    def set_role(
        email: str,
        body: RoleBody,
        user: Annotated[Me, Depends(require(Action.MANAGE_ROLES))],
        store: StoreDep,
    ) -> dict[str, Any]:
        email = email.lower()
        if email == user.email and body.role is not Role.GOVERNANCE_ADMIN:
            raise HTTPException(status_code=400, detail="You cannot remove your own admin role")
        existing = store.get("users", email) or {"created_at": now().isoformat()}
        record = {
            **existing,
            "email": email,
            "role": body.role.value,
            "active": body.active,
            "security_reviewer": body.security_reviewer,
        }
        store.set("users", email, record)
        return record

    # Product analytics

    @app.post("/api/events", status_code=204)
    def product_event(
        body: ProductEvent, user: Annotated[Me, Depends(current_user)], store: StoreDep
    ) -> Response:
        if body.event not in PRODUCT_EVENTS:
            raise HTTPException(status_code=400, detail="unknown event")
        ts = now()
        store.create(
            "product_events",
            uuid.uuid4().hex,
            {
                "event": body.event,
                "app_id": body.app_id,
                "role": user.role.value,
                "source_view": body.source_view,
                "timestamp": ts.isoformat(),
            },
        )
        return Response(status_code=204)

    _mount_console(app)
    return app


def _mount_console(app: FastAPI) -> None:
    """Serve the built console with a fallback to index.html for client routes."""
    if not (FRONTEND_DIST / "index.html").exists():
        return
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (FRONTEND_DIST / path).resolve()
        if candidate.is_file() and FRONTEND_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
