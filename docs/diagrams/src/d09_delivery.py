"""09 Delivery: checks, image, deploy, smoke checks, teardown, and the public demo."""

from pathlib import Path

from drawio import Page

CHECKS = (
    "<b>GitHub Actions on every push</b>\n"
    "ruff, mypy, pytest (memory and file stores)\n"
    "Firestore emulator tests\n"
    "forbidden-dependency scan of both lockfiles\n"
    "frontend typecheck, build, contrast\n"
    "Playwright scenarios\n"
    "demo engine parity and bundle scan"
)
SMOKE = (
    "<b>scripts/smoke_gcp.sh</b>\n"
    "no sign-in: stopped at IAP\n"
    "forged header: stopped at IAP and in the backend\n"
    "executive viewer cannot write\n"
    "submitter cannot approve their own gate\n"
    "one live triage call settles its cost\n"
    "export run twice: same row count"
)


def build(path: Path) -> None:
    p = Page(
        "09  Delivery",
        1800,
        860,
        "From a push to a verified deployment, then teardown; the public demo ships from the same repository",
    )
    p.zone("Google Cloud project", 860, 100, 900, 520, align="right")
    p.zone("Runtime", 1300, 160, 420, 380, fill="blue", align="right")

    p.card("repo", "Repository\nmain branch", 30, 290, 170, 64)
    p.card("ci", "GitHub Actions\nCI", 270, 290, 170, 64, kind="decision")
    p.note("checks", CHECKS, 190, 430, 330, 150)
    p.card(
        "pages",
        "GitHub Pages\nindex.html and the\ninteractive console",
        270,
        120,
        170,
        76,
        kind="ok",
    )
    p.card("deploy", "scripts/deploy_gcp.sh\nidempotent steps", 540, 290, 210, 64)
    p.icon("build", "Cloud Build", 920, 296, "Cloud Build", 52, side="top")
    p.icon(
        "registry",
        "Artifact Registry",
        1110,
        296,
        "Artifact Registry\nimage per commit",
        52,
        side="top",
    )
    p.icon("iap", "Identity-Aware Proxy", 1350, 240, "IAP", 52)
    p.icon("service", "Cloud Run", 1560, 240, "Console service", 52)
    p.icon("sched", "Cloud Scheduler", 1350, 400, "Two nightly\nschedules", 52)
    p.icon("jobs", "Cloud Run", 1560, 400, "Four jobs", 52, side="right")
    p.note("smoke", SMOKE, 470, 640, 350, 150)
    p.card(
        "teardown",
        "scripts/teardown_gcp.sh\nremoves every billed resource\nand lists anything left",
        960,
        677,
        280,
        76,
        kind="muted",
    )

    p.edge("repo", "ci", "push")
    p.edge("checks", "ci", kind="optional_secondary", out="T", into="B")
    p.edge("ci", "pages", "green", kind="success", out="T", into="B")
    p.edge("ci", "deploy", "green", kind="success")
    p.edge("deploy", "build", "source")
    p.edge("build", "registry", "image")
    p.edge(
        "registry",
        "service",
        "deploy --iap",
        out="R",
        into="T",
        points=[(1240, 322), (1240, 135), (1586, 135)],
    )
    p.edge("registry", "jobs", out="R", into="B", points=[(1240, 322), (1240, 580), (1586, 580)])
    p.edge("iap", "service", "verified\nassertion")
    p.edge("sched", "jobs", kind="secondary")
    p.edge("deploy", "smoke", "then", out="B", into="T")
    p.edge("smoke", "teardown", "same day,\nafter recording", kind="secondary")
    p.legend(30, 640, ("primary", "optional_secondary", "secondary", "success"))
    p.write(path)
