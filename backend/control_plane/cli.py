"""The ``cp`` command line."""

import json
import os
from typing import Annotated, NoReturn

import typer

from control_plane.settings import Settings, UnsafeBindError, assert_safe_bind, get_settings

app = typer.Typer(help="Enterprise AI Control Plane", no_args_is_help=True)
data_app = typer.Typer(help="Banking77 data import and splits (M2)", no_args_is_help=True)
users_app = typer.Typer(help="User and role management (M4)", no_args_is_help=True)
app.add_typer(data_app, name="data")
app.add_typer(users_app, name="users")


def _not_yet(milestone: str) -> NoReturn:
    typer.echo(f"Not implemented until {milestone}.", err=True)
    raise typer.Exit(code=2)


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Bind address")] = None,
    port: Annotated[int | None, typer.Option(help="Bind port")] = None,
    reload: Annotated[bool, typer.Option(help="Reload on code changes")] = False,
) -> None:
    """Run the API and console."""
    import uvicorn

    base = get_settings()
    bind_host = host or base.bind_host
    bind_port = port or base.bind_port
    settings = Settings(bind_host=bind_host, bind_port=bind_port)
    try:
        assert_safe_bind(settings)
    except UnsafeBindError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    # Child processes re-read the environment, so pin the checked host there too.
    os.environ["BIND_HOST"] = bind_host
    uvicorn.run(
        "control_plane.api:create_app",
        factory=True,
        host=bind_host,
        port=bind_port,
        reload=reload,
        access_log=False,  # access logs could carry query text; keep them off
    )


@app.command("seed-fixture")
def seed_fixture_cmd() -> None:
    """Load fixture users and FIXTURE apps into the configured store."""
    from control_plane.fixtures import seed_fixture
    from control_plane.settings import StoreBackend
    from control_plane.store import build_store

    settings = get_settings()
    if settings.store_backend is StoreBackend.MEMORY:
        typer.echo("Memory store seeds itself on startup; nothing to do.")
        return
    users, apps = seed_fixture(build_store(settings))
    typer.echo(f"Seeded {users} fixture users and {apps} FIXTURE apps.")


@data_app.command("fetch")
def data_fetch() -> None:
    """Download Banking77 at a pinned commit and verify hashes."""
    from control_plane.triage.dataset import fetch

    for line in fetch():
        typer.echo(line)
    typer.echo("Headers, 77 labels, and sensitive intents verified.")


@data_app.command("split")
def data_split() -> None:
    """Create the development, training, frozen evaluation, and shadow splits."""
    from control_plane.triage.dataset import make_splits

    for name, info in make_splits().items():
        typer.echo(f"{name}: {info['row_count']} rows, sha256 {info['sha256'][:12]}")


@app.command()
def train(name: Annotated[str, typer.Argument()] = "classifier_v1") -> None:
    """Train classifier_v1 on the training split and calibrate it on dev."""
    from control_plane.triage.evaluate import train_classifier

    record = train_classifier(name)
    typer.echo(json.dumps(record, indent=2))


@app.command()
def freeze(config_id: Annotated[str, typer.Argument()] = "classifier_v1") -> None:
    """Tune thresholds on dev, then create the policy and config (create only)."""
    from control_plane.triage.evaluate import FreezeError, freeze_classifier

    try:
        frozen = freeze_classifier(config_id)
    except FreezeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(frozen["policy"]["tuning"], indent=2))
    typer.echo(f"Frozen {frozen['policy']['policy_id']} and {config_id}.")


@app.command()
def evaluate(
    config_id: Annotated[str, typer.Argument()],
    rerun_reason: Annotated[
        str | None, typer.Option(help="Required to run a config on the frozen set again")
    ] = None,
) -> None:
    """Run a frozen config once on the frozen evaluation set and write its scorecard."""
    from control_plane.triage.evaluate import FreezeError, evaluate_config, triage_settings

    kind = triage_settings()["configs"][config_id]["kind"]
    try:
        if kind == "llm":
            from control_plane.triage.llm_eval import evaluate_llm_config

            provider, store, settings = _live(config_id)
            out = evaluate_llm_config(
                config_id,
                provider=provider,
                store=store,
                settings=settings,
                rerun_reason=rerun_reason,
                progress=_progress,
            )
        else:
            out = evaluate_config(config_id, rerun_reason)
    except FreezeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Experiment {out['experiment']['experiment_id']}")
    for key, metric in out["scorecard"].items():
        typer.echo(f"  {key}: {metric.value} {metric.unit} [{metric.provenance}]")


# Live model commands


def _live_store(settings: Settings):  # type: ignore[no-untyped-def]
    from control_plane.settings import StoreBackend
    from control_plane.store import build_store

    if settings.store_backend is StoreBackend.MEMORY:
        typer.echo(
            "Paid runs need a durable ledger. Set STORE_BACKEND=file (or firestore).", err=True
        )
        raise typer.Exit(code=1)
    return build_store(settings)


def _live(config_id: str):  # type: ignore[no-untyped-def]
    from control_plane.providers import build_provider
    from control_plane.settings import ProviderMode
    from control_plane.triage.evaluate import triage_settings
    from control_plane.triage.preflight import require_preflight

    settings = get_settings()
    if settings.provider_mode is ProviderMode.FIXTURE:
        typer.echo("Set PROVIDER_MODE=gemini_api or vertex for live runs.", err=True)
        raise typer.Exit(code=1)
    spec = triage_settings()["configs"][config_id]
    model_id = getattr(settings, spec["model_setting"])
    try:
        require_preflight(settings.provider_mode.value, model_id)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    provider = build_provider(settings, spec["thinking_level"])
    return provider, _live_store(settings), settings


def _progress(done: int, total: int, call) -> None:  # type: ignore[no-untyped-def]
    if done == total or done % 25 == 0:
        typer.echo(f"  {done}/{total} (last: {call.status}, cached={call.from_cache})")


@app.command()
def pilot(
    config_id: Annotated[str, typer.Argument()],
    n: Annotated[int, typer.Option(help="Dev tuning cases to run")] = 50,
) -> None:
    """Run a small dev-only pilot and project the cost of the full M3 plan."""
    from control_plane.triage.llm_eval import RunPausedError
    from control_plane.triage.llm_eval import pilot as run_pilot

    provider, store, settings = _live(config_id)
    try:
        report = run_pilot(
            config_id, n, provider=provider, store=store, settings=settings, progress=_progress
        )
    except RunPausedError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=3) from exc
    typer.echo(json.dumps(report, indent=2))


@app.command()
def tune(config_id: Annotated[str, typer.Argument()]) -> None:
    """Tune an LLM config's agreement threshold on dev, then freeze policy and config."""
    from control_plane.triage.evaluate import FreezeError
    from control_plane.triage.llm_eval import RunPausedError, tune_and_freeze

    provider, store, settings = _live(config_id)
    try:
        frozen = tune_and_freeze(
            config_id, provider=provider, store=store, settings=settings, progress=_progress
        )
    except (FreezeError, RunPausedError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(frozen["policy"]["tuning"], indent=2))


@app.command()
def ledger() -> None:
    """Show budget totals at paid-tier list prices."""
    from control_plane.budget import Ledger
    from control_plane.triage.llm_eval import _ledger

    settings = get_settings()
    lg: Ledger = _ledger(_live_store(settings), settings)
    for budget_id, b in sorted(lg.totals().items()):
        typer.echo(
            f"{budget_id}: committed ${b['committed_micros'] / 1e6:.4f}, reserved "
            f"${b['reserved_micros'] / 1e6:.4f}, limit ${b['limit_usd_micros'] / 1e6:.2f}"
        )


@app.command("experiment-report")
def experiment_report() -> None:
    """Regenerate docs/experiment_report.md from experiment artifacts."""
    from control_plane.triage.report import REPORT_PATH, generate

    generate()
    typer.echo(f"Wrote {REPORT_PATH}")


@app.command()
def preflight() -> None:
    """Verify model access, structured output, and token counting for both models."""
    from control_plane.providers import build_provider
    from control_plane.settings import ProviderMode
    from control_plane.triage.preflight import run_preflight

    settings = get_settings()
    if settings.provider_mode is ProviderMode.FIXTURE:
        typer.echo("Set PROVIDER_MODE=gemini_api or vertex first.", err=True)
        raise typer.Exit(code=1)
    report = run_preflight(
        [settings.vertex_low_cost_model, settings.vertex_high_capability_model],
        provider=build_provider(settings),
        store=_live_store(settings),
        settings=settings,
        thinking_level="minimal",
    )
    typer.echo(json.dumps(report, indent=2))
    if not report["passed"]:
        raise typer.Exit(code=1)


@app.command()
def pricecheck(
    backend: Annotated[str, typer.Option(help="gemini_api or vertex")] = "gemini_api",
) -> None:
    """Fetch the official pricing page and write a versioned price card."""
    from control_plane.pricing import PriceCheckError, fetch_price_card

    settings = get_settings()
    try:
        path = fetch_price_card(
            backend, [settings.vertex_low_cost_model, settings.vertex_high_capability_model]
        )
    except PriceCheckError as exc:
        typer.echo(f"Price check failed, nothing written: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(path.read_text())


@app.command()
def importregistry() -> None:
    """Import an organization's app list from CSV plus a column mapping."""
    _not_yet("M4")


@users_app.command("set-role")
def users_set_role() -> None:
    """Assign a role to a user."""
    _not_yet("M4")


@app.command()
def shadow() -> None:
    """Replay simulated days through the approved and candidate configs."""
    _not_yet("M5")


@app.command()
def drill() -> None:
    """Run the incident drill on simulated days 10 to 12."""
    _not_yet("M5")


@app.command()
def export() -> None:
    """Export events and results to BigQuery idempotently."""
    _not_yet("M6")


@app.command()
def report() -> None:
    """Generate docs/executive_report.md from the analytics queries."""
    _not_yet("M6")


@app.command()
def snapshot() -> None:
    """Export read-only JSON for the static snapshot console."""
    _not_yet("M7")


if __name__ == "__main__":
    app()
