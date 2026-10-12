"""08 Monitoring and incident: the drill, as recorded in docs/incident_report.md."""

from pathlib import Path

from drawio import Page

SIGNALS = (
    "<b>Daily signals</b>\n"
    "review rate\n"
    "cost per correct case\n"
    "accuracy on a seeded 10% labeled sample"
)
POLICY = (
    "<b>Alert policy, frozen before the drill</b>\n"
    "baseline: simulated days 1 to 7\n"
    "mean plus or minus 3 standard deviations,\n"
    "with a minimum margin per signal"
)


def build(path: Path) -> None:
    p = Page(
        "08  Monitoring and incident",
        1800,
        700,
        "The incident drill on the production classifier, as recorded in docs/incident_report.md",
    )
    p.zone("Every simulated day", 30, 110, 560, 360, fill="purple")
    p.zone(
        "Simulated day 10: detected the day the drift began · MEASURED",
        960,
        110,
        810,
        220,
        fill="pink",
    )

    p.card("traffic", "Shadow traffic\nSIMULATED", 60, 170, 200, 64)
    p.card(
        "drift", "40 drift cases, days 10 to 12\nFIXTURE, authored", 60, 330, 220, 64, kind="muted"
    )
    p.note("signals", SIGNALS, 330, 220, 230, 110)
    p.note("policy", POLICY, 620, 90, 300, 104)
    p.card("check", "Any signal past\nits threshold?", 680, 240, 180, 70, kind="decision")
    p.card(
        "incident",
        "Incident opened\nreview rate 0.2177\nagainst 0.2172",
        1000,
        236,
        200,
        78,
        kind="bad",
    )
    p.card("pause", "governance_admin\npauses automation", 1270, 240, 200, 70, kind="bad")
    p.card("rollback", "Rollback\nevery case goes to\nhuman review", 1540, 236, 200, 78)
    p.card(
        "resume",
        "Day 13: a shadow check passes every\nthreshold; automation resumes",
        1500,
        420,
        280,
        70,
        kind="ok",
    )
    p.card("next", "No breach: the\nnext day is checked", 680, 420, 180, 64, kind="muted")
    p.note(
        "margin",
        "Detection margin was 0.0006, and no other\nsignal breached: the report recommends a\ndrift-specific signal before relying on these alerts.",
        900,
        420,
        400,
        80,
    )

    p.edge("traffic", "signals", out="R", into="L", points=[(300, 202), (300, 275)])
    p.edge("drift", "signals", out="R", into="L", points=[(300, 362), (300, 275)])
    p.edge("signals", "check")
    p.edge("policy", "check", kind="optional_secondary", out="B", into="T")
    p.edge("check", "incident", "yes", kind="failure")
    p.edge("check", "next", "no", kind="success", out="B", into="T")
    p.edge("incident", "pause", kind="failure")
    p.edge("pause", "rollback")
    p.edge("rollback", "resume", kind="success", out="B", into="T")
    p.edge("incident", "margin", kind="optional_secondary", out="B", into="T")
    p.legend(30, 510, ("primary", "optional_secondary", "success", "failure"))
    p.write(path)
