"""11 Public demo: the GitHub Pages console runs the real backend in the visitor's browser."""

from pathlib import Path

from drawio import Page

FILES = (
    "<b>Static files on GitHub Pages</b>\n"
    "console assets\n"
    "snapshot JSON for the first paint\n"
    "backend bundle.zip, SHA-256 checked\n"
    "Pyodide runtime and frozen packages,\nSHA-256 locked"
)
PARITY = (
    "<b>CI parity test</b>\n"
    "81 scripted requests, every role, replayed\n"
    "against the native app and the browser engine:\n"
    "identical statuses and bodies"
)


def build(path: Path) -> None:
    p = Page(
        "11  Public demo",
        1700,
        820,
        "The GitHub Pages console runs the unchanged backend inside the visitor's browser; nothing a visitor does leaves the tab",
    )
    p.zone("Browser tab", 380, 100, 900, 560)
    p.zone("Web Worker", 740, 160, 500, 450, fill="blue")
    p.zone("Not in the demo", 1320, 100, 350, 300, dashed=True)

    p.note("files", FILES, 30, 100, 300, 150)
    p.card("visitor", "Visitor", 60, 330, 160, 56)
    p.card("console", "Console\nthe same React app", 430, 326, 220, 64)
    p.card("snapshot", "First paint from\nexported JSON", 430, 500, 220, 64, kind="muted")
    p.card(
        "app",
        "The unchanged FastAPI\nbackend (in-process ASGI)",
        790,
        326,
        240,
        64,
        kind="decision",
    )
    p.card("store", "Memory store\nSYNTHETIC registry +\ncommitted evidence", 1070, 320, 150, 76)
    p.card("runtime", "Pyodide\nPython 3.13 in WebAssembly", 790, 480, 240, 64)
    p.card(
        "no_llm",
        "Live model calls\nMEASURED numbers come\nfrom the committed runs",
        1350,
        160,
        290,
        76,
        kind="muted",
    )
    p.card(
        "no_text",
        "Banking77 message text\nonly the label list ships",
        1350,
        280,
        290,
        64,
        kind="muted",
    )
    p.note("parity", PARITY, 745, 690, 330, 100)

    p.edge("visitor", "console", "opens")
    p.edge(
        "files",
        "console",
        "loaded once,\ncached",
        kind="secondary",
        out="R",
        into="T",
        points=[(540, 175)],
    )
    p.edge("console", "snapshot", "until the engine\nis ready", kind="secondary", out="B", into="T")
    p.edge("console", "app", "every API\nrequest")
    p.edge("app", "store")
    p.edge("runtime", "app", "runs", kind="secondary", out="T", into="B")
    p.edge("parity", "runtime", kind="success", out="T", into="B")
    p.legend(30, 600, ("primary", "secondary", "success"))
    p.write(path)
