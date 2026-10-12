"""13 Data lineage: where every BigQuery table comes from and what reads it (analytics/export.py)."""

from pathlib import Path

from drawio import Page

# (source label, source kind, table, row center y)
ROWS = [
    ("apps\none document per application", "fs", "app_snapshots", 290),
    ("apps/{app}/events\nappend-only lifecycle events", "fs", "app_events", 370),
    ("attempts\nbudget ledger, one per model call", "fs", "attempts", 450),
    ("incidents\nopened by monitoring", "fs", "incidents", 530),
    ("product_events\nconsole usage analytics", "fs", "product_events", 610),
    (
        "artifacts/experiments/*/results.jsonl\nfrozen evaluation runs (MEASURED)",
        "git",
        "experiment_results",
        750,
    ),
    (
        "artifacts/shadow/*/comparisons.jsonl\nshadow replay (SIMULATED)",
        "git",
        "shadow_results",
        830,
    ),
]

NOT_EXPORTED = (
    "<b>Stays in Firestore, never exported</b>\n"
    "users and roles, configs, policies, releases,\n"
    "reviews, notes, routed_cases (case text),\n"
    "budgets, assist_scores, assist_dismissals"
)
STEPS = (
    "<b>Every arrow runs through the same nightly export</b>\n"
    "1  build rows; drop any field that could carry text\n"
    "2  write JSONL per table to Cloud Storage\n"
    "3  load into the table's _staging twin (fresh each run)\n"
    "4  MERGE on event_id after ROW_NUMBER dedup\n"
    "Re-running it changes nothing: same row count."
)


def build(path: Path) -> None:
    p = Page(
        "13  Data lineage",
        1800,
        1080,
        "Where each BigQuery table comes from and what reads it: Firestore and committed evidence, through the nightly export, to the console and reports",
    )
    p.zone("Firestore · operational store", 30, 220, 360, 440, fill="orange")
    p.zone("Repository · committed evidence", 30, 676, 360, 200, fill="purple")
    p.zone("Nightly cp-export · Cloud Run job, 02:30 UTC", 430, 90, 500, 960, dashed=True)
    p.zone("BigQuery · control_plane", 960, 220, 290, 730, fill="blue")
    p.zone("Readers · analytics/queries.py", 1290, 220, 480, 730, fill="green")

    p.icon("job", "Cloud Run", 470, 130, "cp-export", 44)
    p.icon("gcs", "Cloud Storage", 600, 130, "JSONL", 44)
    p.icon("staging", "BigQuery", 720, 130, "_staging", 44)
    p.card("merge", "MERGE on\nevent_id", 820, 128, 90, 48, kind="decision")
    p.edge("job", "gcs", kind="secondary")
    p.edge("gcs", "staging", kind="secondary")
    p.edge("staging", "merge", kind="secondary")
    p.note("steps", STEPS, 460, 880, 440, 150)

    for i, (label, kind, table, y) in enumerate(ROWS):
        src = p.card(f"src{i}", label, 50, y - 30, 320, 60)
        dst = p.card(f"t_{table}", table, 990, y - 22, 230, 44, kind="decision")
        p.edge(src, dst, kind="primary" if kind == "fs" else "secondary")
    p.card("t_export_runs", "export_runs", 990, 888, 230, 44, kind="muted")
    p.note("not_exported", NOT_EXPORTED, 30, 900, 360, 100)
    p.edge(
        "merge",
        "t_export_runs",
        "one row per run",
        kind="optional_secondary",
        out="R",
        into="L",
        points=[(945, 152), (945, 910)],
        label_pos=0.75,
    )

    p.card(
        "flow",
        "Console Flow page\nweekly enter, advance, stall, exit;\nmedian days per stage; leaderboard",
        1320,
        332,
        420,
        76,
    )
    p.card(
        "portfolio",
        "Spend and value by app and platform\n(latest snapshot per app)",
        1320,
        260,
        420,
        60,
    )
    p.card(
        "value",
        "docs/executive_report.md\nSupport Triage monthly net value by config",
        1320,
        720,
        420,
        60,
    )
    p.card("freshness", "Console: time of the last export", 1320, 888, 420, 44)
    p.card(
        "adhoc",
        "Not read by a console query yet:\nattempts, incidents, product_events, shadow_results\n(available for ad hoc analysis)",
        1320,
        500,
        420,
        76,
        kind="muted",
    )

    p.edge("t_app_snapshots", "portfolio")
    p.edge("t_app_events", "flow")
    p.edge(
        "t_app_snapshots",
        "flow",
        "join on app_id",
        points=[(1262, 290), (1262, 370)],
        label_pos=0.4,
    )
    p.edge("t_experiment_results", "value")
    p.edge("t_export_runs", "freshness")
    p.legend(1290, 970, ("primary", "secondary", "optional_secondary"))
    p.write(path)
