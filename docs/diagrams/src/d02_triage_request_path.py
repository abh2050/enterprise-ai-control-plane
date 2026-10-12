"""02 Triage request path: one case through the budget ledger, the configs, and the policy."""

from pathlib import Path

from drawio import Page

RULES = (
    "<b>Decision policy: first matching rule wins</b>\n"
    "1  sensitive intent: review\n"
    "2  out_of_scope: abstain\n"
    "3  classifier probability at or above its threshold: auto\n"
    "4  LLM agrees with the classifier and probability at or\n"
    "    above the agreement threshold: auto\n"
    "5  intent outside the eligible cohort: review\n"
    "6  otherwise: review\n"
    "Thresholds were tuned on the dev split and frozen.\n"
    "LLM self-reported confidence is never used."
)


def build(path: Path) -> None:
    p = Page(
        "02  Triage request path",
        1760,
        1110,
        "One customer message through the budget ledger, the three configs, and the decision policy",
    )
    p.zone("Budget ledger · one Firestore transaction", 240, 110, 560, 340, fill="orange")
    p.zone("Three configs on identical cases", 840, 110, 320, 560, fill="blue")
    p.zone("Settlement", 690, 730, 440, 250, fill="green")
    p.text("Both LLM configs settle the same way.", 706, 955, 260, 20)

    p.card("case", "Customer message\none case", 30, 291, 170, 70)
    p.icon("count", "Vertex AI", 300, 300, "count_tokens\nat most 8,000 input", 52)
    p.icon(
        "reserve",
        "Firestore",
        640,
        300,
        "Reserve at the price card\napp-day, experiment, total\ncaps; at most 2 attempts",
        52,
    )
    p.card("exhausted", "budget_exhausted\nno call made", 566, 150, 200, 64, kind="bad")

    p.card("clf", "classifier_v1\nTF-IDF + logistic regression\nno model spend", 870, 140, 260, 76)
    p.icon(
        "flash",
        "Vertex AI",
        960,
        380,
        "llm_high_capability_v1\ngemini-3.8-flash, cached prefix",
        52,
    )
    p.icon("lite", "Vertex AI", 960, 590, "llm_low_cost_v1\ngemini-3.1-flash-lite", 52, side="top")

    p.card("policy", "Deterministic\ndecision policy", 1240, 371, 200, 70, kind="decision")
    p.note("rules", RULES, 1170, 640, 470, 186)
    p.card("auto", "auto route", 1540, 250, 160, 56, kind="ok")
    p.card("review", "human review", 1540, 378, 160, 56)
    p.card("abstain", "abstain", 1540, 506, 160, 56, kind="muted")

    p.icon(
        "settle",
        "Firestore",
        960,
        840,
        "Settle actual cost,\nrelease the reservation once\n(within 30 s, at most\n256 output tokens)",
        52,
    )
    p.card(
        "unknown", "unknown\nreservation held,\nno automatic retry", 705, 830, 175, 76, kind="bad"
    )

    p.edge("case", "count")
    p.edge("count", "reserve", "reservation")
    p.edge("reserve", "exhausted", "cap reached", kind="failure", out="T", into="B")
    p.edge("reserve", "flash", "admitted, sent", kind="success", points=[(800, 326), (800, 406)])
    p.edge("reserve", "lite", kind="success", points=[(800, 326), (800, 616)])
    p.edge(
        "case",
        "clf",
        "the classifier runs on every case",
        out="T",
        into="L",
        points=[(115, 90), (822, 90), (822, 178)],
    )
    p.edge("clf", "policy", "label, probability", points=[(1190, 178), (1190, 406)])
    p.edge("flash", "policy", "label")
    p.edge("lite", "policy", points=[(1190, 616), (1190, 406)])
    p.edge(
        "rules",
        "policy",
        kind="optional_secondary",
        out="T",
        into="B",
        points=[(1405, 560), (1340, 560)],
    )
    p.edge("policy", "auto", kind="success", points=[(1490, 406), (1490, 278)])
    p.edge("policy", "review")
    p.edge("policy", "abstain", kind="secondary", points=[(1490, 406), (1490, 534)])
    p.edge("lite", "settle", kind="success", out="B", into="T")
    p.edge(
        "lite",
        "unknown",
        "lost response",
        kind="failure",
        out="B:0.2",
        into="T",
        points=[(970, 790), (792, 790)],
    )
    p.legend(30, 930, ("primary", "optional_secondary", "success", "failure"))
    p.write(path)
