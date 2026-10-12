"""The ``cp`` command line."""

import json
import os
import uuid
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


@app.command("seed-registry")
def seed_registry_cmd() -> None:
    """Load fixture users and the SYNTHETIC registry seed into the configured store."""
    from control_plane.fixtures import seed_registry
    from control_plane.settings import StoreBackend
    from control_plane.store import build_store

    settings = get_settings()
    if settings.store_backend is StoreBackend.MEMORY:
        typer.echo("The memory store seeds itself on startup; nothing to do.")
        return
    counts = seed_registry(build_store(settings))
    typer.echo(f"Seeded {counts}")


@data_app.command("fetch")
def data_fetch() -> None:
    """Download Banking77 at a pinned commit and verify hashes."""
    from control_plane.triage.dataset import fetch

    for line in fetch():
        typer.echo(line)
    typer.echo("Headers, 77 labels, and sensitive intents verified.")


model_app = typer.Typer(help="Frozen classifier binary", no_args_is_help=True)
app.add_typer(model_app, name="model")


@model_app.command("fetch")
def model_fetch() -> None:
    """Download the frozen classifier binary from MODEL_BUCKET and verify its hash."""
    import hashlib
    import importlib

    from control_plane.triage.classifier import MODEL_DIR
    from control_plane.triage.evaluate import _read

    settings = get_settings()
    if not settings.model_bucket:
        typer.echo("Set MODEL_BUCKET.", err=True)
        raise typer.Exit(code=1)
    storage = importlib.import_module("google.cloud.storage")
    blob = (
        storage.Client(project=settings.gcp_project)
        .bucket(settings.model_bucket)
        .blob("models/classifier_v1.pkl")
    )
    data = blob.download_as_bytes()
    expected = _read(MODEL_DIR / "classifier_v1.json")["model_sha256"]
    if hashlib.sha256(data).hexdigest() != expected:
        typer.echo("Model hash does not match the frozen record.", err=True)
        raise typer.Exit(code=1)
    (MODEL_DIR / "classifier_v1.pkl").write_bytes(data)
    typer.echo("classifier_v1.pkl verified")


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
            from control_plane.triage.llm_eval import RunPausedError, evaluate_llm_config

            provider, store, settings = _live(config_id)
            try:
                out = evaluate_llm_config(
                    config_id,
                    provider=provider,
                    store=store,
                    settings=settings,
                    rerun_reason=rerun_reason,
                    progress=_progress,
                )
            except RunPausedError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=3) from exc
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
def ledger(
    reconcile: Annotated[
        bool, typer.Option(help="Mark attempts stuck in 'sent' as unknown (after a crash)")
    ] = False,
    export: Annotated[
        bool, typer.Option(help="Write settled spend to artifacts/ledger_summary.json")
    ] = False,
) -> None:
    """Show budget totals at list prices."""
    from control_plane.budget import Ledger
    from control_plane.triage.llm_eval import _ledger

    settings = get_settings()
    lg: Ledger = _ledger(_live_store(settings), settings)
    if reconcile:
        marked = lg.reconcile_sent()
        typer.echo(f"Marked {len(marked)} attempt(s) unknown; their reservations stay held.")
    if export:
        from control_plane.fixtures import LEDGER_SUMMARY

        LEDGER_SUMMARY.write_text(json.dumps(lg.summary(), indent=2) + "\n")
        typer.echo(f"Wrote {LEDGER_SUMMARY}")
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
    from control_plane.triage.evaluate import triage_settings

    models = {}
    for spec in triage_settings()["configs"].values():
        if spec["kind"] == "llm":
            model_id = getattr(settings, spec["model_setting"])
            models[model_id] = (
                build_provider(settings, spec["thinking_level"]),
                spec["thinking_level"],
            )
    report = run_preflight(models, store=_live_store(settings), settings=settings)
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
def importregistry(
    csv_path: Annotated[str, typer.Argument(help="CSV export of your app list")],
    mapping: Annotated[str, typer.Option(help="YAML column mapping")] = (
        "imports/example_mapping.yaml"
    ),
    actor: Annotated[str, typer.Option(help="Recorded as the importer")] = "admin@example.com",
) -> None:
    """Import an organization's app list from CSV plus a column mapping (all or nothing)."""
    from pathlib import Path

    from control_plane.importer import import_csv

    store = _live_store(get_settings())
    report = import_csv(store, Path(csv_path), Path(mapping), actor)
    for err in report.errors:
        typer.echo(f"error: {err}", err=True)
    if report.errors:
        typer.echo(f"Nothing imported: {len(report.errors)} problem(s) in {report.rows} rows.")
        raise typer.Exit(code=1)
    typer.echo(f"Imported {len(report.created)} apps into intake.")


@users_app.command("set-role")
def users_set_role(
    email: Annotated[str, typer.Argument()],
    role: Annotated[
        str, typer.Argument(help="app_owner, reviewer, governance_admin, or executive_viewer")
    ],
    security_reviewer: Annotated[bool, typer.Option()] = False,
) -> None:
    """Assign a role to a user (governance admins also use the Settings page)."""
    from datetime import UTC, datetime

    from control_plane.contracts import Role

    store = _live_store(get_settings())
    existing = store.get("users", email.lower()) or {}
    store.set(
        "users",
        email.lower(),
        {
            "email": email.lower(),
            "role": Role(role).value,
            "active": True,
            "security_reviewer": security_reviewer,
            "created_at": existing.get("created_at", datetime.now(UTC).isoformat()),
        },
    )
    typer.echo(f"{email.lower()} is now {role}.")


@app.command()
def shadow(
    candidate: Annotated[str, typer.Argument()] = "llm_high_capability_v1",
    release_id: Annotated[str | None, typer.Option(help="Attach the run to this release")] = None,
) -> None:
    """Replay 14 simulated days: the approved config decides, the candidate shadows."""
    from control_plane.triage.activation import attach_shadow, latest_release
    from control_plane.triage.llm_eval import RunPausedError
    from control_plane.triage.shadow import run_shadow

    release = latest_release(candidate)
    if release is None:
        typer.echo(f"Propose a release for {candidate} first: cp release propose", err=True)
        raise typer.Exit(code=1)
    provider, store, settings = _live(candidate)
    try:
        summary = run_shadow(
            candidate,
            release["cohort"],
            provider=provider,
            store=store,
            settings=settings,
            progress=_progress,
        )
    except RunPausedError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=3) from exc
    attach_shadow(release_id or release["release_id"], f"artifacts/shadow/{summary['run_id']}")
    typer.echo(json.dumps(summary["totals"], indent=2))


release_app = typer.Typer(
    help="Release proposals and decisions (Section 6.7)", no_args_is_help=True
)
app.add_typer(release_app, name="release")


@release_app.command("propose")
def release_propose(
    candidate: Annotated[str, typer.Argument()],
    proposed_by: Annotated[str, typer.Option()] = "owner@example.com",
) -> None:
    """Propose a release: gates for the full candidate and for the proposed cohort."""
    from control_plane.triage.activation import propose

    record = propose(candidate, proposed_by)
    for key in ("full_candidate", "cohort_candidate"):
        gates = record[key]["gates"]
        typer.echo(f"{key}: {sum(g['passed'] for g in gates)}/{len(gates)} gates pass")
        for g in gates:
            if not g["passed"]:
                typer.echo(f"  FAIL {g['gate']}: observed {g['observed']} vs {g['threshold']}")
    typer.echo(f"Proposed {record['release_id']}; cohort excludes {record['cohort_excluded']}")


@release_app.command("decide")
def release_decide(
    release_id: Annotated[str, typer.Argument()],
    decision: Annotated[
        str, typer.Argument(help="activate_cohort, activate_full, withhold, or reject")
    ],
    rationale: Annotated[str, typer.Option()],
    decided_by: Annotated[str, typer.Option()] = "admin@example.com",
) -> None:
    """Record a governance admin's release decision (final)."""
    from control_plane.triage.activation import ReleaseError, decide

    try:
        record = decide(release_id, decision, rationale, decided_by, "governance_admin")
    except ReleaseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"{record['release_id']}: {record['decision']} by {record['decided_by']}")


monitor_app = typer.Typer(help="Monitoring alert policy (Section 6.8)", no_args_is_help=True)
app.add_typer(monitor_app, name="monitor")


def _latest_shadow_run() -> str:
    from control_plane.monitoring import SHADOW_DIR

    runs = sorted(p.name for p in SHADOW_DIR.glob("shadow_*") if (p / "summary.json").exists())
    if not runs:
        typer.echo("Run cp shadow first.", err=True)
        raise typer.Exit(code=1)
    return runs[-1]


@monitor_app.command("freeze")
def monitor_freeze() -> None:
    """Derive alert thresholds from baseline days 1 to 7 and freeze them (create only)."""
    from control_plane.monitoring import freeze_alert_policy

    policy = freeze_alert_policy(_latest_shadow_run())
    typer.echo(json.dumps(policy["thresholds"], indent=2))


@app.command()
def drill() -> None:
    """Run the incident drill on simulated days 10 to 12 and write the incident report."""
    from control_plane.monitoring import load_drift, run_drill
    from control_plane.pricing import load_price_card
    from control_plane.triage.llm_eval import llm_context, run_llm_calls
    from control_plane.triage.m5_report import incident_report

    run_id = _latest_shadow_run()
    candidate = "llm_high_capability_v1"
    provider, store, settings = _live(candidate)
    ctx = llm_context(candidate, settings)
    drift = load_drift()
    calls = run_llm_calls(
        ctx,
        [(d["case_id"], d["text"]) for d in drift],
        experiment_id=f"drill_{run_id}",
        provider=provider,
        price_card=load_price_card(backend=provider.backend),
        store=store,
        settings=settings,
    )
    record = run_drill(run_id, {c.case_id: c for c in calls})
    incident_report()
    typer.echo(
        json.dumps(
            {
                "detected": record["detected"],
                "incident": record["incident"],
                "timeline": record["timeline"],
            },
            indent=2,
            default=str,
        )
    )


@release_app.command("report")
def release_report() -> None:
    """Regenerate docs/release_recommendation.md from release and shadow artifacts."""
    from control_plane.triage.m5_report import RECOMMENDATION, release_recommendation

    release_recommendation()
    typer.echo(f"Wrote {RECOMMENDATION}")


@app.command()
def export(
    local: Annotated[str | None, typer.Option(help="Write JSONL here instead of BigQuery")] = None,
) -> None:
    """Export events and results to BigQuery idempotently (staging, then MERGE)."""
    from pathlib import Path

    from control_plane.analytics.export import export as run_export
    from control_plane.analytics.export import write_local
    from control_plane.store import build_store

    settings = get_settings()
    store = build_store(settings)
    if local:
        counts = write_local(store, Path(local))
    else:
        if not settings.export_bucket:
            typer.echo("Set EXPORT_BUCKET.", err=True)
            raise typer.Exit(code=1)
        counts = run_export(store, settings.gcp_project, settings.export_bucket)
    typer.echo(json.dumps(counts))


@app.command()
def report() -> None:
    """Generate docs/executive_report.md from the BigQuery analytics queries."""
    from control_plane.analytics.report import REPORT, generate

    generate(get_settings().gcp_project)
    typer.echo(f"Wrote {REPORT}")


@monitor_app.command("nightly")
def monitor_nightly() -> None:
    """Nightly job: re-score Governance Assist for every app."""
    from control_plane.assist import score_all
    from control_plane.store import build_store

    scores = score_all(build_store(get_settings()))
    flagged = sum(s["flagged"] for s in scores)
    typer.echo(json.dumps({"scored": len(scores), "flagged": flagged}))


smoke_app = typer.Typer(help="Deployment smoke checks (Section 10)", no_args_is_help=True)
app.add_typer(smoke_app, name="smoke")


@smoke_app.command("triage")
def smoke_triage() -> None:
    """One live triage call through the ledger; fails unless its cost settles."""
    from control_plane.budget import call_with_budget
    from control_plane.contracts import AttemptStatus, Limits
    from control_plane.pricing import load_price_card
    from control_plane.providers import build_provider
    from control_plane.triage.llm_eval import _ledger
    from control_plane.triage.preflight import PROBE_LABELS, PROBE_PROMPT

    settings = get_settings()
    store = _live_store(settings)
    provider = build_provider(settings, "minimal")
    model = settings.vertex_low_cost_model
    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": [*PROBE_LABELS, "out_of_scope"]},
            "rationale": {"type": "string", "maxLength": 300},
        },
        "required": ["intent", "rationale"],
    }
    outcome = call_with_budget(
        _ledger(store, settings),
        provider,
        load_price_card(backend=provider.backend).price(model),
        Limits(max_output_tokens=256),
        app_id="support-triage",
        experiment_id="smoke",
        case_id=f"smoke-{uuid.uuid4().hex[:12]}",
        model_id=model,
        prompt=PROBE_PROMPT,
        response_schema=schema,
    )
    attempt = store.get("attempts", outcome.attempt_id) or {}
    settled = (
        outcome.status is AttemptStatus.COMPLETED
        and attempt.get("status") == "completed"
        and attempt.get("actual_micros") is not None
    )
    typer.echo(
        json.dumps(
            {
                "attempt": outcome.attempt_id,
                "status": attempt.get("status"),
                "actual_micros": attempt.get("actual_micros"),
                "reserved_micros": attempt.get("reserved_micros"),
                "settled": settled,
            }
        )
    )
    if not settled:
        raise typer.Exit(code=1)


@smoke_app.command("auth")
def smoke_auth() -> None:
    """In-container check: the deployed config rejects forged and missing IAP assertions."""
    from fastapi.testclient import TestClient

    from control_plane.api import create_app
    from control_plane.auth import IAP_HEADER
    from control_plane.settings import IdentityMode

    settings = get_settings()
    if settings.identity_mode is not IdentityMode.IAP or not settings.iap_audience:
        typer.echo("Run with IDENTITY_MODE=iap and IAP_AUDIENCE set.", err=True)
        raise typer.Exit(code=1)
    client = TestClient(create_app(settings), client=("10.0.0.1", 443))
    forged = (
        "eyJhbGciOiJFUzI1NiIsImtpZCI6ImZvcmdlZCJ9."
        "eyJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIn0.c2lnbmF0dXJl"
    )
    results = {
        "missing": client.get("/api/me").status_code,
        "forged": client.get("/api/me", headers={IAP_HEADER: forged}).status_code,
        "fixture_header": client.get(
            "/api/me", headers={"X-Fixture-User": "admin@example.com"}
        ).status_code,
    }
    typer.echo(json.dumps(results))
    if any(code != 401 for code in results.values()):
        raise typer.Exit(code=1)


@app.command()
def snapshot(
    out: Annotated[str, typer.Option(help="Folder the snapshot build serves")] = (
        "frontend/.snapshot-data"
    ),
    at: Annotated[str, typer.Option(help="Fixed clock, ISO 8601")] = "2026-10-12T12:00:00+00:00",
) -> None:
    """Export read-only JSON for the static snapshot console."""
    from datetime import datetime
    from pathlib import Path

    from control_plane.snapshot import export

    count = export(Path(out), datetime.fromisoformat(at))
    typer.echo(f"Wrote {count} snapshot files to {out}/snapshot")


if __name__ == "__main__":
    app()
