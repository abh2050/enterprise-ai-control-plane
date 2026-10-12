"""03 Registry lifecycle: nine stages, gate rules, and the managed versus external branch."""

from pathlib import Path

from drawio import Page

GATES = (
    "<b>Review gates by risk tier</b> (configs/lifecycle.yaml)\n"
    "low: one reviewer\n"
    "medium: governance review (governance_admin)\n"
    "high: governance + security review\n"
    "The submitter can never approve.\n"
    "Approvals stay valid for 180 days."
)


def build(path: Path) -> None:
    p = Page(
        "03  Registry lifecycle",
        1980,
        900,
        "Nine stages; the server validates every move against configs/lifecycle.yaml and the caller's role",
    )
    p.zone(
        "Managed apps only: inference runs through the control plane",
        820,
        110,
        920,
        200,
        fill="blue",
    )
    p.zone("From any stage · governance_admin, with a reason", 880, 600, 860, 200, dashed=True)

    p.card("intake", "intake\nowner and a problem\nof 30 or more words", 40, 400, 200, 80)
    p.card(
        "case",
        "business_case\nvolume, value hypothesis,\ncost estimate (ASSUMPTION)",
        300,
        400,
        220,
        80,
    )
    p.card("gates", "review_gates", 580, 405, 170, 70, kind="decision")
    p.note("rules", GATES, 500, 600, 330, 140)
    p.card("evaluation", "evaluation\nscorecard on frozen cases", 860, 180, 220, 80)
    p.card("shadow", "shadow\nthe candidate never decides", 1180, 180, 220, 80)
    p.card("activation", "controlled_activation\ncohort or full release", 1500, 180, 220, 80)
    p.card("monitored", "monitored", 1790, 405, 150, 70, kind="ok")
    p.card("paused", "paused\nresumes at its prior stage", 960, 660, 240, 80, kind="muted")
    p.card("retired", "retired\nkept for the audit trail", 1420, 660, 240, 80, kind="muted")

    p.edge("intake", "case", "owner")
    p.edge("case", "gates", "owner submits")
    p.edge(
        "gates",
        "evaluation",
        "gates approved,\nmanaged config",
        kind="success",
        points=[(790, 440), (790, 220)],
    )
    p.edge("evaluation", "shadow", "every gate\npasses", kind="success")
    p.edge("shadow", "activation", "release\ndecision", kind="success")
    p.edge(
        "activation",
        "monitored",
        "activated",
        kind="success",
        out="R",
        into="T",
        points=[(1865, 220)],
    )
    p.edge(
        "gates",
        "monitored",
        "external app (Copilot, Abacus, custom): governance_admin publishes",
        label_pos=0.15,
    )
    p.edge(
        "gates",
        "case",
        "sent back with a reason",
        kind="failure",
        out="T",
        into="T",
        points=[(665, 340), (410, 340)],
    )
    p.edge("rules", "gates", kind="optional_secondary", out="T", into="B")
    p.legend(40, 640, ("primary", "optional_secondary", "success", "failure"))
    p.write(path)
