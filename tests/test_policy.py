"""Required test 6 (core): a sensitive prediction always routes to review."""

import itertools

import pytest

from control_plane.contracts import ConfigKind, Route
from control_plane.triage.policy import PolicyParams, route, tune_classifier_threshold

SENS = frozenset({"lost_or_stolen_card", "compromised_card"})
LABELS = ["card_arrival", "lost_or_stolen_card", "compromised_card", "out_of_scope"]


@pytest.mark.parametrize("threshold", [0.0, 0.3, 0.99, 1.0])
@pytest.mark.parametrize("agreement", [None, 0.0, 0.5])
@pytest.mark.parametrize("prob", [0.0, 0.5, 1.0])
def test_sensitive_always_reviews(threshold: float, agreement: float | None, prob: float) -> None:
    for cohort in (None, frozenset(LABELS)):
        p = PolicyParams(threshold, SENS, agreement, cohort)
        for clf_label, llm_label in itertools.product(LABELS[:3], LABELS):
            if clf_label not in SENS and llm_label not in SENS:
                continue
            assert route(p, ConfigKind.LLM, clf_label, prob, llm_label) is Route.REVIEW
            if clf_label in SENS:
                assert route(p, ConfigKind.CLASSIFIER, clf_label, prob) is Route.REVIEW


def test_rules_in_order() -> None:
    p = PolicyParams(0.8, SENS, 0.5, frozenset({"card_arrival"}))
    assert route(p, ConfigKind.CLASSIFIER, "card_arrival", 0.9) is Route.AUTO
    assert route(p, ConfigKind.CLASSIFIER, "card_arrival", 0.7) is Route.REVIEW
    assert route(p, ConfigKind.LLM, "card_arrival", 0.1, "out_of_scope") is Route.ABSTAIN
    assert route(p, ConfigKind.LLM, "card_arrival", 0.6, "card_arrival") is Route.AUTO
    assert route(p, ConfigKind.LLM, "card_arrival", 0.4, "card_arrival") is Route.REVIEW
    assert route(p, ConfigKind.LLM, "top_up_failed", 0.9, "card_arrival") is Route.REVIEW
    # outside the eligible cohort never automates
    assert route(p, ConfigKind.CLASSIFIER, "top_up_failed", 0.99) is Route.REVIEW


def test_tuning_maximizes_coverage_at_target() -> None:
    refs = ["a"] * 100
    labels = ["a"] * 90 + ["b"] * 10
    probs = [0.9] * 90 + [0.4] * 10
    choice = tune_classifier_threshold(labels, probs, refs, frozenset(), 0.95, min_auto=10)
    assert choice.dev_auto_precision == 1.0 and choice.dev_auto_count == 90
    assert 0.4 < choice.threshold <= 0.9
