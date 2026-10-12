"""12 BigQuery schema: the control_plane dataset (infra/bigquery.sql) and how its tables join."""

from pathlib import Path

from drawio import Page

FACT = "#4284F3"
DIMENSION = "#1E8E3E"
OPS = "#80868B"

TS = [("event_ts", "TIMESTAMP", ""), ("event_date", "DATE", "PART")]

APP_EVENTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("kind", "STRING", ""),
    ("from_stage", "STRING", ""),
    ("to_stage", "STRING", ""),
    ("actor", "STRING", ""),
    ("reason", "STRING", ""),
    ("source", "STRING", ""),
    *TS,
]
APP_SNAPSHOTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "KEY CLUSTER"),
    ("name", "STRING", ""),
    ("platform", "STRING", ""),
    ("owner", "STRING", ""),
    ("business_unit", "STRING", ""),
    ("stage", "STRING", ""),
    ("risk_tier", "STRING", ""),
    ("monthly_spend_usd", "FLOAT64", ""),
    ("spend_provenance", "STRING", ""),
    ("monthly_value_usd", "FLOAT64", ""),
    ("value_provenance", "STRING", ""),
    ("provenance", "STRING", ""),
    *TS,
]
EXPERIMENT_RESULTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("experiment_id", "STRING", "FK"),
    ("config_id", "STRING", ""),
    ("case_id", "STRING", ""),
    ("predicted_label", "STRING", ""),
    ("reference_label", "STRING", ""),
    ("route", "STRING", ""),
    ("correct", "BOOL", ""),
    ("latency_ms", "INT64", ""),
    ("input_tokens", "INT64", ""),
    ("output_tokens", "INT64", ""),
    ("cost_micros", "INT64", ""),
    ("attempt_count", "INT64", ""),
    *TS,
]
ATTEMPTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("experiment_id", "STRING", "KEY"),
    ("model_id", "STRING", ""),
    ("status", "STRING", ""),
    ("reserved_micros", "INT64", ""),
    ("actual_micros", "INT64", ""),
    ("input_tokens", "INT64", ""),
    ("output_tokens", "INT64", ""),
    ("cached_tokens", "INT64", ""),
    *TS,
]
INCIDENTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("signal", "STRING", ""),
    ("threshold", "FLOAT64", ""),
    ("observed", "FLOAT64", ""),
    ("status", "STRING", ""),
    ("provenance", "STRING", ""),
    ("opened_at", "TIMESTAMP", ""),
    ("closed_at", "TIMESTAMP", ""),
    *TS,
]
PRODUCT_EVENTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("event", "STRING", ""),
    ("role", "STRING", ""),
    ("source_view", "STRING", ""),
    *TS,
]
SHADOW_RESULTS = [
    ("event_id", "STRING", "PK"),
    ("app_id", "STRING", "FK CLUSTER"),
    ("run_id", "STRING", ""),
    ("simulated_day", "INT64", ""),
    ("case_id", "STRING", ""),
    ("approved_label", "STRING", ""),
    ("candidate_label", "STRING", ""),
    ("approved_route", "STRING", ""),
    ("candidate_route", "STRING", ""),
    ("label_agree", "BOOL", ""),
    ("route_agree", "BOOL", ""),
    ("candidate_cost_micros", "INT64", ""),
    *TS,
]
EXPORT_RUNS = [
    ("run_id", "STRING", "PK"),
    ("exported_at", "TIMESTAMP", "PART"),
    ("counts", "STRING", ""),
]

NOTES = (
    "<b>How to read this</b>\n"
    "Dataset control_plane (US), created by infra/bigquery.sql.\n"
    "Every table is partitioned by event_date and clustered by app_id.\n"
    "PK: the MERGE key; a nightly re-export cannot double-count.\n"
    "BigQuery has no foreign keys: the lines are the joins the\n"
    "queries use (analytics/queries.py). app_snapshots holds one row\n"
    "per app per day; its latest row is the current app.\n"
    "Each table has a _staging twin loaded fresh before the MERGE.\n"
    "No message text is exported (export.py checks every row)."
)


def build(path: Path) -> None:
    p = Page(
        "12  BigQuery schema",
        1760,
        1230,
        "The control_plane dataset: eight tables, their keys, and how the analytics queries join them",
    )

    ev = p.table(
        "app_events",
        "app_events",
        APP_EVENTS,
        40,
        110,
        subtitle="lifecycle events · from Firestore apps/*/events",
        header=FACT,
    )
    snap = p.table(
        "app_snapshots",
        "app_snapshots",
        APP_SNAPSHOTS,
        700,
        110,
        w=340,
        subtitle="one row per app per day · from Firestore apps",
        header=DIMENSION,
    )
    inc = p.table(
        "incidents",
        "incidents",
        INCIDENTS,
        1380,
        110,
        subtitle="monitoring incidents · from Firestore incidents",
        header=FACT,
    )
    exp = p.table(
        "experiment_results",
        "experiment_results",
        EXPERIMENT_RESULTS,
        40,
        470,
        subtitle="one row per case per frozen run · from artifacts/experiments",
        header=FACT,
    )
    att = p.table(
        "attempts",
        "attempts",
        ATTEMPTS,
        700,
        600,
        w=340,
        subtitle="budget ledger, one row per model call · from Firestore attempts",
        header=FACT,
    )
    pev = p.table(
        "product_events",
        "product_events",
        PRODUCT_EVENTS,
        1380,
        470,
        subtitle="console usage analytics · from Firestore product_events",
        header=FACT,
    )
    sha = p.table(
        "shadow_results",
        "shadow_results",
        SHADOW_RESULTS,
        1380,
        740,
        subtitle="one row per case per shadow run · from artifacts/shadow",
        header=FACT,
    )
    p.table(
        "export_runs",
        "export_runs",
        EXPORT_RUNS,
        700,
        1000,
        w=340,
        subtitle="one row per nightly export · last export time",
        header=OPS,
    )

    p.relation(ev["app_id"], snap["app_id"], out="R", into="L", label="app_id")
    p.relation(exp["app_id"], snap["app_id"], out="R", into="L", points=[(560, 554), (560, 194)])
    p.relation(
        exp["experiment_id"],
        att["experiment_id"],
        out="R",
        into="L",
        points=[(620, 578), (620, 708)],
        label="experiment_id",
    )
    p.relation(att["app_id"], snap["app_id"], out="L", into="L", points=[(660, 684), (660, 194)])
    p.relation(inc["app_id"], snap["app_id"], out="L", into="R", label="app_id", label_pos=-0.55)
    p.relation(pev["app_id"], snap["app_id"], out="L", into="R", points=[(1200, 554), (1200, 194)])
    p.relation(sha["app_id"], snap["app_id"], out="L", into="R", points=[(1240, 824), (1240, 194)])

    p.note("notes", NOTES, 40, 960, 600, 176)
    p.text("<b>Green</b>: the app dimension", 1060, 1150, 260, 20, 12, DIMENSION)
    p.text("<b>Blue</b>: append-only fact tables", 1060, 1172, 260, 20, 12, FACT)
    p.text("<b>Grey</b>: export bookkeeping", 1060, 1194, 260, 20, 12, OPS)
    p.text(
        "Crow's foot: many rows to one app, or many results to one experiment",
        1320,
        1150,
        420,
        40,
        12,
    )
    p.write(path)
