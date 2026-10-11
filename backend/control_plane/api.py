"""FastAPI application: JSON API under /api and the built console at /."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from control_plane.auth import FIXTURE_HEADER, Action, current_user, get_store, require
from control_plane.contracts import (
    App,
    AppCard,
    AppEvent,
    DataMode,
    DatasetLabel,
    IncidentStatus,
    Me,
    Metric,
    ModeInfo,
    PortfolioSummary,
    Provenance,
    Stage,
)
from control_plane.fixtures import seed_fixture
from control_plane.settings import (
    MICROS_PER_USD,
    IdentityMode,
    ProviderMode,
    Settings,
    StoreBackend,
    assert_safe_bind,
    get_settings,
)
from control_plane.store import Store, build_store

STALL_DAYS = 30
PRODUCTION_STAGES = {Stage.CONTROLLED_ACTIVATION, Stage.MONITORED}
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _now() -> datetime:
    return datetime.now(UTC)


def _load_apps(store: Store) -> list[App]:
    return sorted((App.model_validate(d) for d in store.list("apps")), key=lambda a: a.name)


def _days_in_stage(app: App, now: datetime) -> int:
    return max(0, (now - app.stage_entered_at).days)


def _number_provenance(apps: list[App], default: Provenance) -> Provenance:
    """FIXTURE data taints every number derived from it."""
    if any(a.provenance == Provenance.FIXTURE for a in apps):
        return Provenance.FIXTURE
    return default


def _data_mode(settings: Settings) -> DataMode:
    if settings.provider_mode is ProviderMode.VERTEX:
        return DataMode.LIVE
    return DataMode.FIXTURE


def create_app(settings: Settings | None = None, store: Store | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        assert_safe_bind(settings)
        if (
            settings.store_backend is StoreBackend.MEMORY
            and settings.identity_mode is IdentityMode.FIXTURE
        ):
            seed_fixture(app.state.store)
        yield

    app = FastAPI(title="Enterprise AI Control Plane", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store if store is not None else build_store(settings)

    StoreDep = Annotated[Store, Depends(get_store)]

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/mode")
    def mode(store: StoreDep) -> ModeInfo:
        present = {d.get("provenance") for d in store.list("apps")}
        labels = [label for label in DatasetLabel if label.value in present]
        return ModeInfo(
            data_mode=_data_mode(settings),
            identity_mode=settings.identity_mode.value,
            provider_mode=settings.provider_mode.value,
            store_backend=settings.store_backend.value,
            dataset_labels=labels,
        )

    @app.get("/api/me")
    def me(user: Annotated[Me, Depends(current_user)]) -> Me:
        return user

    @app.get("/api/fixture/users")
    def fixture_users(store: StoreDep) -> list[dict[str, Any]]:
        """Lists sign-in choices for the local identity switcher. Fixture mode only."""
        if settings.identity_mode is not IdentityMode.FIXTURE:
            raise HTTPException(status_code=404)
        return [{"email": u["email"], "role": u["role"]} for u in store.list("users")]

    @app.get("/api/portfolio/summary")
    def portfolio_summary(
        _: Annotated[Me, Depends(require(Action.READ_PORTFOLIO))], store: StoreDep
    ) -> PortfolioSummary:
        now = _now()
        apps = _load_apps(store)
        counts = _number_provenance(apps, Provenance.MEASURED)
        live = [a for a in apps if a.stage is not Stage.RETIRED]
        cases = [a.business_case for a in apps if a.business_case is not None]
        value = sum(c.monthly_value_usd.value for c in cases) if cases else None
        incidents = [i for i in store.list("incidents") if i.get("status") == IncidentStatus.OPEN]

        def count(n: int, source: str) -> Metric:
            return Metric(value=n, unit="apps", provenance=counts, source=source)

        return PortfolioSummary(
            total_apps=count(len(live), "apps (excluding retired)"),
            apps_in_production=count(sum(a.stage in PRODUCTION_STAGES for a in apps), "apps.stage"),
            apps_stalled=count(
                sum(
                    _days_in_stage(a, now) > STALL_DAYS and a.stage is not Stage.RETIRED
                    for a in apps
                ),
                "apps.stage_entered_at",
            ),
            monthly_model_spend_usd=Metric(
                value=sum(a.monthly_spend_micros for a in apps) / MICROS_PER_USD,
                unit="USD/month",
                provenance=counts,
                source="apps.monthly_spend_micros",
            ),
            estimated_monthly_value_usd=Metric(
                value=value,
                unit="USD/month",
                provenance=_number_provenance(apps, Provenance.ASSUMPTION),
                source="apps.business_case.monthly_value_usd",
            ),
            open_incidents=Metric(
                value=len(incidents), unit="incidents", provenance=counts, source="incidents"
            ),
            approvals_waiting=count(
                sum(a.stage is Stage.REVIEW_GATES for a in apps), "apps in review_gates"
            ),
            apps_by_stage={s: count(sum(a.stage is s for a in apps), "apps.stage") for s in Stage},
        )

    @app.get("/api/apps")
    def list_apps(
        _: Annotated[Me, Depends(require(Action.READ_PORTFOLIO))], store: StoreDep
    ) -> list[AppCard]:
        now = _now()
        cards = []
        for a in _load_apps(store):
            prov = _number_provenance([a], Provenance.MEASURED)
            cards.append(
                AppCard(
                    app_id=a.app_id,
                    name=a.name,
                    owner=a.owner,
                    business_unit=a.business_unit,
                    platform=a.platform,
                    stage=a.stage,
                    risk_tier=a.risk_tier,
                    days_in_stage=Metric(
                        value=_days_in_stage(a, now),
                        unit="days",
                        provenance=prov,
                        source=f"apps/{a.app_id}.stage_entered_at",
                    ),
                    monthly_spend_usd=Metric(
                        value=a.monthly_spend_micros / MICROS_PER_USD,
                        unit="USD/month",
                        provenance=prov,
                        source=f"apps/{a.app_id}.monthly_spend_micros",
                    ),
                    provenance=a.provenance,
                )
            )
        return cards

    @app.get("/api/apps/{app_id}")
    def get_app(
        app_id: str,
        _: Annotated[Me, Depends(require(Action.READ_APP_DETAIL))],
        store: StoreDep,
    ) -> App:
        doc = store.get("apps", app_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="app not found")
        return App.model_validate(doc)

    @app.get("/api/apps/{app_id}/events")
    def app_events(
        app_id: str,
        _: Annotated[Me, Depends(require(Action.READ_APP_DETAIL))],
        store: StoreDep,
    ) -> list[AppEvent]:
        events = [AppEvent.model_validate(d) for d in store.list(f"apps/{app_id}/events")]
        return sorted(events, key=lambda e: e.created_at)

    @app.get("/api/incidents")
    def incidents(
        _: Annotated[Me, Depends(require(Action.READ_INCIDENTS))], store: StoreDep
    ) -> list[dict[str, Any]]:
        return store.list("incidents")

    @app.get("/api/reviews/pending")
    def pending_reviews(
        _: Annotated[Me, Depends(require(Action.READ_REVIEWS))],
    ) -> list[dict[str, Any]]:
        return []  # gate and routed-case queues arrive in M4 and M5

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


__all__ = ["FIXTURE_HEADER", "create_app"]
