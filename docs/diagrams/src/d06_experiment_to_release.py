"""06 Experiment to release: how the measured evidence produced the recorded decision."""

from pathlib import Path

from drawio import Page

GATES = (
    "<b>Release gates</b> (configs/release_gates.yaml)\n"
    "recall on every sensitive intent: 0.95 or more\n"
    "auto precision: breakeven + 0.03 or more\n"
    "macro F1: at most 0.02 below the baseline\n"
    "p95 latency: 10 s or less\n"
    "risk-suite sensitive routing: 1.0"
)


def build(path: Path) -> None:
    p = Page(
        "06  Experiment to release",
        1800,
        780,
        "Measured evidence to a recorded decision (docs/experiment_report.md, docs/release_recommendation.md)",
    )
    p.zone("Development split only", 40, 110, 520, 190, fill="purple")
    p.zone("Frozen evaluation · MEASURED", 600, 110, 560, 190, fill="blue")
    p.zone(
        "Recorded decisions · docs/release_recommendation.md",
        40,
        420,
        1290,
        180,
        fill="grey",
        align="right",
    )

    p.card("tune", "Tune thresholds\non the dev split", 70, 180, 200, 70)
    p.card("freeze", "Freeze the policy\ncreate-only record", 320, 180, 200, 70)
    p.card("frozen", "1,540 identical cases\nthree configs, same order", 630, 180, 230, 70)
    p.card("scorecard", "Scorecard\nten metrics, bootstrap CIs", 900, 180, 230, 70)
    p.card("gates", "Gates", 1220, 180, 150, 70, kind="decision")
    p.note("rules", GATES, 1420, 140, 350, 150)

    p.card(
        "lite",
        "gemini-3.1-flash-lite\npasses 3 of 10 gates\ndecision: reject",
        70,
        480,
        220,
        84,
        kind="bad",
    )
    p.card(
        "flash",
        "gemini-3.8-flash\n5 of 10 gates as a full release,\n4 of 6 as the proposed cohort",
        340,
        480,
        250,
        84,
        kind="bad",
    )
    p.card(
        "shadow",
        "Shadow replay, 14 simulated days\n85.5% label agreement (SIMULATED)\n$1.65 model spend (MEASURED)",
        680,
        480,
        280,
        84,
    )
    p.card(
        "decision",
        "governance_admin: withhold\nclassifier_v1 stays\nauthoritative",
        1040,
        480,
        260,
        84,
        kind="decision",
    )
    p.card("activation", "Cohort activation\nnot reached", 1440, 487, 200, 70, kind="muted")

    p.edge("tune", "freeze")
    p.edge("freeze", "frozen", "before any\nfrozen run")
    p.edge("frozen", "scorecard")
    p.edge("scorecard", "gates")
    p.edge("rules", "gates", kind="optional_secondary", out="L", into="R")
    p.edge("gates", "lite", kind="failure", out="B", into="T", points=[(1295, 370), (180, 370)])
    p.edge(
        "gates",
        "flash",
        "the cohort still fails macro F1\nand cash withdrawal recall",
        kind="failure",
        out="B",
        into="T",
        points=[(1295, 370), (465, 370)],
        label_pos=0.82,
    )
    p.edge("flash", "shadow", "replayed")
    p.edge("shadow", "decision")
    p.edge("decision", "activation", "blocked while\ngates fail", kind="secondary")
    p.legend(40, 640, ("primary", "optional_secondary", "secondary", "failure"))
    p.write(path)
