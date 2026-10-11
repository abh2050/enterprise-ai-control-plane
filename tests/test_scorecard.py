"""Required test 8: scorecard metrics match a hand-computed fixture."""

import pytest

from control_plane.contracts import Provenance, Route
from control_plane.triage.scorecard import (
    CaseResult,
    Economics,
    RiskResult,
    build_scorecard,
    paired_bootstrap,
)

A, R, X = Route.AUTO, Route.REVIEW, Route.ABSTAIN
LABELS = ["a", "b", "s"]
SENSITIVE = frozenset({"s"})

# id, reference, predicted, route, latency, cost
FIXTURE = [
    ("1", "a", "a", A, 100, 1000),
    ("2", "a", "a", A, 200, 1000),
    ("3", "a", "b", A, 300, 1000),
    ("4", "b", "b", R, 400, 1000),
    ("5", "b", None, X, 500, 1000),
    ("6", "s", "s", R, 600, 1000),
    ("7", "s", "a", A, 700, 1000),
    ("8", "b", "b", A, 800, 1000),
    ("9", "s", "s", R, 900, 1000),
    ("10", "a", "a", R, 1000, 1000),
]
RESULTS = [CaseResult(*row) for row in FIXTURE]
RISK = [
    RiskResult("r1", "sensitive_indirect", R, R),
    RiskResult("r2", "sensitive_indirect", R, A),
    RiskResult("r3", "out_of_domain", X, X),
]


def card(econ: Economics | None = None):  # type: ignore[no-untyped-def]
    return build_scorecard(RESULTS, LABELS, SENSITIVE, RISK, Provenance.MEASURED, "fixture", econ)


def test_hand_computed_metrics() -> None:
    c = card()
    # Per label TP/FP/FN, abstain counted as a miss:
    #   a: TP 3 (1,2,10) FP 1 (7)  FN 1 (3)      F1 = 6/8  = 0.75
    #   b: TP 2 (4,8)    FP 1 (3)  FN 1 (5)      F1 = 4/6  = 0.6667
    #   s: TP 2 (6,9)    FP 0      FN 1 (7)      F1 = 4/5  = 0.8
    assert c["macro_f1"].value == pytest.approx((0.75 + 4 / 6 + 0.8) / 3)
    assert c["accuracy"].value == pytest.approx(0.7)
    assert c["automation_coverage"].value == pytest.approx(0.5)  # 1,2,3,7,8
    assert c["auto_precision"].value == pytest.approx(3 / 5)  # 1,2,8 correct
    assert c["review_rate"].value == pytest.approx(0.4)
    assert c["abstention_rate"].value == pytest.approx(0.1)
    assert c["latency_p50_ms"].value == 500  # nearest rank: ceil(5) = 5th
    assert c["latency_p95_ms"].value == 1000  # ceil(9.5) = 10th
    assert c["model_cost_per_1k_usd"].value == pytest.approx(1.0)  # 1000 micros each
    assert c["sensitive_recall.s"].value == pytest.approx(2 / 3)
    assert c["sensitive_review_rate.s"].value == pytest.approx(2 / 3)
    assert c["risk_route_accuracy.sensitive_indirect"].value == pytest.approx(0.5)
    assert c["risk_route_accuracy.out_of_domain"].value == pytest.approx(1.0)
    assert c["total_cost_per_correct_usd"].value is None
    assert all(
        m.provenance is Provenance.MEASURED
        for k, m in c.items()
        if k != "total_cost_per_correct_usd"
    )


def test_total_cost_per_correct_is_assumption() -> None:
    econ = Economics(
        review_cost_usd=2.0, misroute_cost_standard_usd=10.0, misroute_cost_sensitive_usd=50.0
    )
    c = card(econ)
    # model 0.01 + review 5 non-auto x 2 = 10 + misroutes: case 3 (b, standard) 10 + case 7 (s) 50
    # handled = 10 - 2 wrong autos = 8
    assert c["total_cost_per_correct_usd"].value == pytest.approx((0.01 + 10 + 60) / 8)
    assert c["total_cost_per_correct_usd"].provenance is Provenance.ASSUMPTION


def test_paired_bootstrap_identical_is_zero_and_needs_pairs() -> None:
    from control_plane.triage.scorecard import auto_precision

    point, lo, hi = paired_bootstrap(RESULTS, RESULTS, auto_precision, resamples=200)
    assert point == 0 and lo == 0 and hi == 0
    with pytest.raises(ValueError):
        paired_bootstrap(RESULTS, RESULTS[:-1], auto_precision)


def test_paired_bootstrap_detects_improvement() -> None:
    from control_plane.triage.scorecard import macro_f1

    better = [
        CaseResult(r.case_id, r.reference_label, r.reference_label, Route.AUTO, 1, 0)
        for r in RESULTS
    ]
    point, lo, hi = paired_bootstrap(
        RESULTS, better, lambda rs: macro_f1(rs, LABELS), resamples=300
    )
    assert point is not None and point > 0 and lo is not None and lo >= 0
