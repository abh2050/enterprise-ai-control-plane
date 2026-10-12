"""04 Identity and access: IAP verification, Firestore roles, least-privilege service accounts."""

from pathlib import Path

from drawio import Page

ROWS = [
    (
        "cp-console",
        "the console service",
        {
            "Firestore": "datastore.user",
            "BigQuery": "dataViewer on control_plane,\njobUser",
            "Cloud Run": "run.invoker on\nthe four jobs",
        },
    ),
    (
        "cp-jobs",
        "the four Cloud Run jobs",
        {
            "Firestore": "datastore.user",
            "BigQuery": "dataEditor on control_plane,\njobUser",
            "Vertex AI": "aiplatform.user",
            "Cloud Storage": "objectAdmin on\nthe bucket",
        },
    ),
    (
        "cp-scheduler",
        "Cloud Scheduler",
        {"Cloud Run": "run.invoker on cp-monitor\nand cp-export only"},
    ),
    (
        "IAP service agent",
        "Identity-Aware Proxy",
        {"Cloud Run": "run.invoker on\nthe console service"},
    ),
]
COLUMNS = {
    "Firestore": 760,
    "BigQuery": 980,
    "Vertex AI": 1200,
    "Cloud Storage": 1400,
    "Cloud Run": 1600,
}


def build(path: Path) -> None:
    p = Page(
        "04  Identity and access",
        1800,
        1120,
        "Who can reach the console, how the backend checks it, and what each service account may touch",
    )
    p.zone("Google Cloud project", 240, 200, 1530, 280, align="right")
    p.zone("Console service · runs as cp-console", 470, 236, 420, 190, fill="blue")

    p.card("people", "People and smoke-test\nservice accounts", 30, 291, 180, 70)
    p.icon(
        "iap", "Identity-Aware Proxy", 300, 300, "Identity-Aware Proxy\nallow-listed principals", 52
    )
    p.card("reject", "401, or a redirect to\nGoogle sign-in", 226, 96, 200, 64, kind="bad")
    p.icon("console", "Cloud Run", 510, 300, "Console", 52)
    p.card(
        "verify",
        "Verify the IAP assertion\nES256 signature, Google keys,\nissuer, audience, expiry",
        640,
        284,
        230,
        84,
        kind="decision",
    )
    p.icon(
        "role",
        "Firestore",
        1020,
        300,
        "users collection: the role comes\nfrom here, never from the request",
        52,
    )

    p.edge("people", "iap", "Google sign-in")
    p.edge("iap", "console", "signed\nassertion")
    p.edge("console", "verify")
    p.edge("verify", "role", "valid", kind="success")
    p.edge("iap", "reject", "missing or forged", kind="failure", out="T", into="B")
    p.edge("verify", "reject", "invalid", kind="failure", out="T", into="R", points=[(755, 128)])

    p.zone(
        "Service accounts and their only grants (scripts/deploy_gcp.sh) · no principal holds project Editor",
        240,
        520,
        1530,
        570,
        fill="grey",
    )
    for col, x in COLUMNS.items():
        p.text(f"<b>{col}</b>", x - 68, 565, 140, 20, 13, "#3C4043", align="center")
    for i, (account, runs, grants) in enumerate(ROWS):
        y = 610 + i * 118
        p.icon(f"sa{i}", "Cloud IAM", 290, y, f"<b>{account}</b>\nused by {runs}", 46, side="right")
        for col, grant in grants.items():
            p.icon(f"g{i}{col}", col, COLUMNS[col] - 20, y - 4, grant, 44)
    p.write(path)
