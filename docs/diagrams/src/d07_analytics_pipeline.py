"""07 Analytics pipeline: idempotent export from Firestore to BigQuery, then report queries."""

from pathlib import Path

from drawio import Page

TABLES = (
    "<b>Target tables</b>, partitioned by event_date,\n"
    "clustered by app_id: app_events, app_snapshots,\n"
    "experiment_results, shadow_results, attempts,\n"
    "incidents, product_events. No message text."
)
QUERIES = (
    "<b>Parameterized queries</b>\n"
    "at most 100 MB billed, at most 180 days\n"
    "weekly enter, advance, stall, exit\n"
    "median days per stage\n"
    "spend and value by app and platform\n"
    "Support Triage monthly net value"
)


def build(path: Path) -> None:
    p = Page(
        "07  Analytics pipeline",
        1800,
        780,
        "Nightly, idempotent export from Firestore to BigQuery, then the report queries (analytics/export.py, analytics/queries.py)",
    )
    p.zone("Google Cloud project", 220, 100, 1220, 500, align="right")
    p.zone("BigQuery dataset control_plane · US", 760, 150, 640, 280, fill="blue")

    p.icon("firestore", "Firestore", 280, 300, "Firestore\nevents, attempts,\nincidents", 52)
    p.icon("export", "Cloud Run", 470, 300, "cp-export\nnightly 02:30 UTC", 52, side="top")
    p.card("evidence", "Committed evidence\nexperiment and\nshadow results", 240, 470, 180, 76)
    p.icon("gcs", "Cloud Storage", 650, 300, "Cloud Storage\nJSONL per table", 52)
    p.icon(
        "staging", "BigQuery", 820, 300, "_staging tables\nloaded fresh each run", 52, side="top"
    )
    p.card("merge", "MERGE on event_id\nafter ROW_NUMBER dedup", 960, 292, 200, 68, kind="decision")
    p.icon("tables", "BigQuery", 1280, 300, "Target tables", 52, side="top")
    p.note("tables_note", TABLES, 800, 460, 400, 100)
    p.note("queries", QUERIES, 1480, 120, 300, 140)
    p.card("flow", "Console Flow page", 1500, 320, 260, 56)
    p.card("report", "docs/executive_report.md\nwritten by cp report", 1500, 420, 260, 64)

    p.edge("firestore", "export")
    p.edge("evidence", "export", out="R", into="B", points=[(496, 508)])
    p.edge("export", "gcs", "JSONL")
    p.edge("gcs", "staging", "load job")
    p.edge("staging", "merge")
    p.edge("merge", "tables", "run twice:\nsame row count", kind="success")
    p.edge("tables", "flow", out="R", into="L", points=[(1450, 326), (1450, 348)])
    p.edge("tables", "report", out="R", into="L", points=[(1450, 326), (1450, 452)])
    p.edge("queries", "flow", kind="optional_secondary", out="B", into="T")
    p.legend(20, 620, ("primary", "optional_secondary", "success"))
    p.write(path)
