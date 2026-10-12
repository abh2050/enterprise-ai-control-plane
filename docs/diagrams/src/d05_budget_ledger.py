"""05 Budget ledger: every paid model call moves through these states (budget.py)."""

from pathlib import Path

from drawio import Page

LIMITS = (
    "<b>Admission, in one Firestore transaction</b>\n"
    "app-day limit: $6\n"
    "experiment limit: $10\n"
    "total allowance: $10\n"
    "fewer than 2 attempts for the case"
)


def build(path: Path) -> None:
    p = Page(
        "05  Budget ledger",
        1620,
        760,
        "Every paid model call moves through these states (backend/control_plane/budget.py)",
    )
    p.card("count", "Count input tokens\n(Vertex count_tokens)", 30, 300, 190, 70)
    p.card(
        "price",
        "Reservation\n(input tokens x 1.10) x input price\n+ output cap x output price",
        270,
        293,
        270,
        84,
    )
    p.card("admit", "Room under\nevery limit?", 600, 300, 170, 70, kind="decision")
    p.note("limits", LIMITS, 545, 100, 280, 124)
    p.card("exhausted", "budget_exhausted\nblocked, no call made", 590, 470, 190, 70, kind="bad")
    p.card("sent", "sent\nmarked just before\nthe call", 860, 297, 180, 76)
    p.zone("Outcomes", 1230, 90, 370, 500, fill="grey")
    p.card(
        "settled",
        "settled\nactual cost recorded,\nreservation released once",
        1260,
        120,
        310,
        80,
        kind="ok",
    )
    p.card(
        "released",
        "released\nerror response: Vertex bills\nonly successful responses",
        1260,
        230,
        310,
        80,
        kind="muted",
    )
    p.card(
        "overrun",
        "overrun\nsettle actual, pause the app,\nopen an incident",
        1260,
        340,
        310,
        80,
        kind="bad",
    )
    p.card(
        "unknown",
        "unknown\ntimeout or lost response:\nreservation held, no retry",
        1260,
        450,
        310,
        80,
        kind="bad",
    )
    p.card(
        "reconcile",
        "reconcile\nattempts stuck in sent\nafter a crash",
        860,
        600,
        180,
        80,
        kind="muted",
    )

    p.edge("count", "price")
    p.edge("price", "admit")
    p.edge("limits", "admit", kind="optional_secondary", out="B", into="T")
    p.edge("admit", "exhausted", "no", kind="failure", out="B", into="T")
    p.edge("admit", "sent", "yes: reserved", kind="success")
    p.edge(
        "sent",
        "settled",
        "response",
        kind="success",
        points=[(1100, 335), (1100, 160)],
        label_pos=0.6,
    )
    p.edge(
        "sent",
        "released",
        "HTTP error",
        kind="secondary",
        points=[(1100, 335), (1100, 270)],
        label_pos=0.6,
    )
    p.edge(
        "sent",
        "overrun",
        "cost above\nreservation",
        kind="failure",
        points=[(1100, 335), (1100, 380)],
        label_pos=0.6,
    )
    p.edge(
        "sent",
        "unknown",
        "timeout",
        kind="failure",
        points=[(1100, 335), (1100, 490)],
        label_pos=0.6,
    )
    p.edge(
        "reconcile", "unknown", "marks", kind="secondary", out="R", into="B", points=[(1415, 640)]
    )
    p.legend(30, 560, ("primary", "optional_secondary", "success", "failure"))
    p.write(path)
