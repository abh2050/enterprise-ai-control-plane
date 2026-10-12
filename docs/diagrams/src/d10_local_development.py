"""10 Local development: everything runs offline except paid model calls."""

from pathlib import Path

from drawio import Page

IDENTITY = (
    "<b>Fixture identity</b>\n"
    "X-Fixture-User header; the role is read\n"
    "from the users collection\n"
    "refuses to bind beyond 127.0.0.1 or localhost\n"
    "rejects non-loopback clients on every request"
)


def build(path: Path) -> None:
    p = Page(
        "10  Local development",
        1620,
        820,
        "Everything runs on one machine and offline, except paid model calls, which go through the budget ledger",
    )
    p.zone("Developer machine", 30, 100, 1280, 680)
    p.zone("Store backends · STORE_BACKEND", 640, 160, 620, 300, fill="blue")
    p.zone("docker compose", 960, 200, 270, 230, dashed=True)

    p.card("vite", "Vite dev server\nReact console", 70, 260, 190, 64)
    p.card("api", "cp serve\nFastAPI on 127.0.0.1", 340, 260, 200, 64, kind="decision")
    p.note("identity", IDENTITY, 280, 110, 320, 120)
    p.card("memory", "memory\ntests and fixture mode", 680, 210, 220, 64)
    p.card("file", "file\nlocked JSON for paid runs", 680, 350, 220, 64)
    p.icon("emulator", "Firestore", 1070, 280, "Firestore emulator", 52)
    p.card(
        "tests",
        "pytest and Playwright\nscenarios, visual baselines,\ndemo parity",
        70,
        450,
        220,
        76,
    )
    p.card(
        "fixture",
        "Fixture provider\ndeterministic, labeled FIXTURE",
        680,
        560,
        260,
        64,
        kind="muted",
    )
    p.icon("vertex", "Vertex AI", 1400, 650, "Vertex AI\npaid runs only,\nthrough the ledger", 52)

    p.edge("vite", "api", "/api proxy")
    p.edge("identity", "api", kind="optional_secondary", out="B", into="T")
    p.edge("api", "memory", out="R", into="L", points=[(600, 292), (600, 242)])
    p.edge("api", "file", out="R", into="L", points=[(600, 292), (600, 382)])
    p.edge("api", "emulator", out="R", into="L", points=[(600, 292), (600, 306)])
    p.edge("tests", "api", kind="secondary", out="R", into="B:0.12", points=[(364, 488)])
    p.edge(
        "api",
        "fixture",
        "PROVIDER_MODE=fixture",
        kind="secondary",
        out="B:0.75",
        into="L",
        points=[(490, 592)],
    )
    p.edge("api", "vertex", "PROVIDER_MODE=vertex", out="B:0.35", into="L", points=[(410, 676)])
    p.legend(1340, 110, ("primary", "optional_secondary", "secondary"))
    p.write(path)
