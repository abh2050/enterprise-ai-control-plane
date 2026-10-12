"""Idempotent export to BigQuery (Section 8).

1. Build rows for each table from the store and the committed artifacts. Every row has a
   stable ``event_id``, so the same fact always maps to the same key. No row carries raw
   message text or note text.
2. Write each table as JSONL to Cloud Storage.
3. Load each file into ``<table>_staging`` (truncating it).
4. MERGE staging into the target after keeping one row per event_id (ROW_NUMBER), so
   running the export twice leaves totals unchanged.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from control_plane.store import Store
from control_plane.triage.dataset import REPO_ROOT

DATASET = "control_plane"
TABLES = [
    "app_events",
    "app_snapshots",
    "experiment_results",
    "shadow_results",
    "attempts",
    "incidents",
    "product_events",
]
EXPERIMENT_DIR = REPO_ROOT / "artifacts" / "experiments"
SHADOW_DIR = REPO_ROOT / "artifacts" / "shadow"


def _ts(value: str | None) -> str | None:
    return datetime.fromisoformat(value).astimezone(UTC).isoformat() if value else None


def _with_time(row: dict[str, Any], ts: str) -> dict[str, Any]:
    stamp = _ts(ts)
    assert stamp is not None
    return {**row, "event_ts": stamp, "event_date": stamp[:10]}


def app_event_rows(store: Store) -> list[dict[str, Any]]:
    return [
        _with_time(
            {
                "event_id": e["event_id"],
                "app_id": e["app_id"],
                "kind": e["kind"],
                "from_stage": e.get("from_stage"),
                "to_stage": e.get("to_stage"),
                "actor": e.get("actor"),
                "reason": e.get("reason"),
                "source": e.get("source"),
            },
            e["created_at"],
        )
        for e in store.list_group("events")
    ]


def app_snapshot_rows(store: Store, now: datetime) -> list[dict[str, Any]]:
    from control_plane.portfolio import Context, card

    ctx = Context(store, now)
    day = now.date().isoformat()
    rows = []
    for a in ctx.apps:
        c = card(a, ctx)
        rows.append(
            _with_time(
                {
                    "event_id": f"{a['app_id']}:{day}",
                    "app_id": a["app_id"],
                    "name": a["name"],
                    "platform": a["platform"],
                    "owner": a.get("owner"),
                    "business_unit": a["business_unit"],
                    "stage": a["stage"],
                    "risk_tier": a["risk_tier"],
                    "monthly_spend_usd": c["monthly_spend_usd"].value,
                    "spend_provenance": c["monthly_spend_usd"].provenance.value,
                    "monthly_value_usd": c["estimated_value_usd"].value,
                    "value_provenance": "ASSUMPTION",
                    "provenance": a.get("provenance"),
                },
                now.isoformat(),
            )
        )
    return rows


def experiment_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for exp_dir in sorted(EXPERIMENT_DIR.glob("exp_*")):
        meta = json.loads((exp_dir / "experiment.json").read_text())
        for line in (exp_dir / "results.jsonl").read_text().splitlines():
            r = json.loads(line)
            rows.append(
                _with_time(
                    {
                        "event_id": f"{meta['experiment_id']}:{r['case_id']}",
                        "app_id": "support-triage",
                        "experiment_id": meta["experiment_id"],
                        "config_id": meta["config_id"],
                        "case_id": r["case_id"],
                        "predicted_label": r["predicted_label"],
                        "reference_label": r["reference_label"],
                        "route": r["route"],
                        "correct": r["correct"],
                        "latency_ms": r["latency_ms"],
                        "input_tokens": r.get("input_tokens", 0),
                        "output_tokens": r.get("output_tokens", 0),
                        "cost_micros": r["cost_micros"],
                        "attempt_count": r.get("attempt_count", 1),
                    },
                    meta["finished_at"],
                )
            )
    return rows


def shadow_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(SHADOW_DIR.glob("shadow_*")):
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        for line in (run_dir / "comparisons.jsonl").read_text().splitlines():
            r = json.loads(line)
            rows.append(
                _with_time(
                    {
                        "event_id": f"{summary['run_id']}:{r['case_id']}",
                        "app_id": "support-triage",
                        "run_id": summary["run_id"],
                        "simulated_day": r["day"],
                        "case_id": r["case_id"],
                        "approved_label": r["approved_label"],
                        "candidate_label": r["candidate_label"],
                        "approved_route": r["approved_route"],
                        "candidate_route": r["candidate_route"],
                        "label_agree": r["label_agree"],
                        "route_agree": r["route_agree"],
                        "candidate_cost_micros": r["candidate_cost_micros"],
                    },
                    summary["finished_at"],
                )
            )
    return rows


def attempt_rows(store: Store) -> list[dict[str, Any]]:
    return [
        _with_time(
            {
                "event_id": a["attempt_id"],
                "app_id": a["app_id"],
                "experiment_id": a["experiment_id"],
                "model_id": a["model_id"],
                "status": a["status"],
                "reserved_micros": a["reserved_micros"],
                "actual_micros": a.get("actual_micros"),
                "input_tokens": a.get("input_tokens"),
                "output_tokens": a.get("output_tokens"),
                "cached_tokens": a.get("cached_tokens"),
            },
            a["created_at"],
        )
        for a in store.list("attempts")
    ]


def incident_rows(store: Store) -> list[dict[str, Any]]:
    return [
        _with_time(
            {
                "event_id": i["incident_id"],
                "app_id": i["app_id"],
                "signal": i["signal"],
                "threshold": float(i["threshold"]),
                "observed": float(i["observed"]),
                "status": i["status"],
                "provenance": i.get("provenance"),
                "opened_at": _ts(i.get("opened_at")),
                "closed_at": _ts(i.get("closed_at")),
            },
            i["opened_at"],
        )
        for i in store.list("incidents")
    ]


def product_event_rows(store: Store) -> list[dict[str, Any]]:
    out = []
    for doc_id, e in ((e.get("event_id") or "", e) for e in store.list("product_events")):
        key = doc_id or f"{e['event']}:{e['timestamp']}:{e.get('app_id')}:{e['role']}"
        out.append(
            _with_time(
                {
                    "event_id": key,
                    "app_id": e.get("app_id"),
                    "event": e["event"],
                    "role": e["role"],
                    "source_view": e["source_view"],
                },
                e["timestamp"],
            )
        )
    return out


def build_rows(store: Store, now: datetime | None = None) -> dict[str, list[dict[str, Any]]]:
    now = now or datetime.now(UTC)
    return {
        "app_events": app_event_rows(store),
        "app_snapshots": app_snapshot_rows(store, now),
        "experiment_results": experiment_rows(),
        "shadow_results": shadow_rows(),
        "attempts": attempt_rows(store),
        "incidents": incident_rows(store),
        "product_events": product_event_rows(store),
    }


FORBIDDEN_KEYS = {"text", "prompt", "prompt_text", "message", "note", "rationale_text"}


def assert_no_text(rows: Iterable[dict[str, Any]]) -> None:
    for r in rows:
        bad = FORBIDDEN_KEYS & r.keys()
        if bad:
            raise ValueError(f"row {r.get('event_id')} carries forbidden fields {bad}")


def merge_sql(project: str, table: str, columns: list[str]) -> str:
    """MERGE staging into target, keeping the newest row per event_id."""
    target = f"`{project}.{DATASET}.{table}`"
    staging = f"`{project}.{DATASET}.{table}_staging`"
    updates = ", ".join(f"T.{c} = S.{c}" for c in columns if c != "event_id")
    cols = ", ".join(columns)
    values = ", ".join(f"S.{c}" for c in columns)
    return (
        f"MERGE {target} T USING (\n"
        f"  SELECT * EXCEPT(rn) FROM (\n"
        f"    SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_ts DESC) AS rn\n"
        f"    FROM {staging}) WHERE rn = 1\n"
        f") S ON T.event_id = S.event_id\n"
        f"WHEN MATCHED THEN UPDATE SET {updates}\n"
        f"WHEN NOT MATCHED THEN INSERT ({cols}) VALUES ({values})"
    )


def export(store: Store, project: str, bucket: str, now: datetime | None = None) -> dict[str, int]:
    import importlib

    from google.cloud import bigquery

    storage = importlib.import_module("google.cloud.storage")

    now = now or datetime.now(UTC)
    tables = build_rows(store, now)
    run_id = f"export_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}"
    bq = bigquery.Client(project=project)
    gcs = storage.Client(project=project).bucket(bucket)
    counts: dict[str, int] = {}
    for table, rows in tables.items():
        assert_no_text(rows)
        counts[table] = len(rows)
        if not rows:
            continue
        blob = gcs.blob(f"exports/{run_id}/{table}.jsonl")
        blob.upload_from_string(
            "".join(json.dumps(r) + "\n" for r in rows), content_type="application/json"
        )
        target = bq.get_table(f"{project}.{DATASET}.{table}")
        staging_id = f"{project}.{DATASET}.{table}_staging"
        job = bq.load_table_from_uri(
            f"gs://{bucket}/exports/{run_id}/{table}.jsonl",
            staging_id,
            job_config=bigquery.LoadJobConfig(
                schema=target.schema,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            ),
        )
        job.result()
        bq.query(merge_sql(project, table, [f.name for f in target.schema])).result()
    bq.query(
        f"INSERT `{project}.{DATASET}.export_runs` (run_id, exported_at, counts) "
        "VALUES (@run_id, @at, @counts)",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("at", "TIMESTAMP", now),
                bigquery.ScalarQueryParameter("counts", "STRING", json.dumps(counts)),
            ]
        ),
    ).result()
    return counts


def write_local(store: Store, out: Path, now: datetime | None = None) -> dict[str, int]:
    """Dry run: write the JSONL files locally without touching GCP."""
    tables = build_rows(store, now)
    out.mkdir(parents=True, exist_ok=True)
    for table, rows in tables.items():
        assert_no_text(rows)
        (out / f"{table}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return {t: len(r) for t, r in tables.items()}
