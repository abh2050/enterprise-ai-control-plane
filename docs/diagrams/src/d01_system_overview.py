"""01 System overview: the deployed control plane on Google Cloud (scripts/deploy_gcp.sh)."""

from pathlib import Path

from drawio import Page


def build(path: Path) -> None:
    p = Page(
        "01  System overview",
        1760,
        1110,
        "What scripts/deploy_gcp.sh creates in one Google Cloud project",
    )
    p.zone("Google Cloud project · us-central1", 220, 90, 1500, 860)
    p.zone("Cloud Run service", 420, 250, 320, 170, fill="blue")
    p.zone(
        "Cloud Run jobs · run as cp-jobs · read and write Firestore",
        420,
        500,
        620,
        420,
        fill="blue",
    )
    p.zone("Managed services", 1180, 120, 520, 810, dashed=True)

    p.card("people", "People\nowners, reviewers,\nadmins, executives", 24, 300, 170, 80)
    p.icon("iap", "Identity-Aware Proxy", 290, 314, "Identity-Aware\nProxy", 52)
    p.icon("console", "Cloud Run", 520, 314, "Console\nFastAPI + React", 52)
    p.icon("sched", "Cloud Scheduler", 290, 640, "Cloud Scheduler", 52)
    p.icon("monitor", "Cloud Run", 560, 540, "cp-monitor", 52)
    p.icon("export", "Cloud Run", 560, 824, "cp-export", 52)
    p.icon("evaluate", "Cloud Run", 860, 540, "cp-evaluate", 52)
    p.icon("shadow", "Cloud Run", 860, 690, "cp-shadow", 52)

    p.icon("firestore", "Firestore", 1260, 314, "Firestore\nregistry, ledger, events", 52)
    p.icon("bigquery", "BigQuery", 1500, 314, "BigQuery\ncontrol_plane", 52, side="right")
    p.icon("vertex", "Vertex AI", 1260, 540, "Vertex AI\nGemini", 52)
    p.icon("secrets", "Secret Manager", 1260, 690, "Secret Manager\nenabled, holds no keys", 52)
    p.icon("gcs", "Cloud Storage", 1260, 824, "Cloud Storage\nexports, classifier", 52)

    p.edge("people", "iap", "HTTPS")
    p.edge("iap", "console", "signed JWT")
    p.edge("console", "firestore", "registry, roles, events", points=[(760, 340)])
    p.edge(
        "console",
        "bigquery",
        "Flow and reports",
        out="R",
        into="T",
        points=[(760, 340), (760, 180), (1526, 180)],
    )
    p.edge(
        "console",
        "evaluate",
        "run on demand",
        out="R",
        into="T",
        points=[(760, 340), (760, 460), (886, 460)],
    )
    p.edge(
        "sched", "monitor", "nightly 02:00 UTC", kind="secondary", points=[(470, 666), (470, 566)]
    )
    p.edge("sched", "export", "02:30 UTC", kind="secondary", points=[(470, 666), (470, 850)])
    p.edge("evaluate", "vertex", "budgeted model calls", points=[(1100, 566)], label_pos=-0.45)
    p.edge("shadow", "vertex", out="R", into="L", points=[(1100, 716), (1100, 566)])
    p.edge("export", "gcs", "JSONL, no message text", kind="secondary")
    p.edge(
        "gcs",
        "bigquery",
        "load, then MERGE",
        kind="secondary",
        out="R",
        into="B",
        points=[(1526, 850)],
    )
    p.legend(220, 980, ("primary", "secondary"))
    p.write(path)
