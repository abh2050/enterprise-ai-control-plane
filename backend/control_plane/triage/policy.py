"""Deterministic routing policy (Section 6.3).

Routes each case to auto, review, or abstain from model labels and the classifier's
calibrated probability. LLM self-reported confidence is never an input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from control_plane.contracts import ConfigKind, Route
from control_plane.triage.dataset import OUT_OF_SCOPE


@dataclass(frozen=True)
class PolicyParams:
    classifier_threshold: float
    sensitive_intents: frozenset[str]
    agreement_threshold: float | None = None
    # None means every intent is eligible for automation.
    eligible_cohort: frozenset[str] | None = field(default=None)


def route(
    params: PolicyParams,
    kind: ConfigKind,
    classifier_label: str,
    classifier_prob: float,
    llm_label: str | None = None,
) -> Route:
    """Apply the six rules in order of precedence."""
    if kind is ConfigKind.LLM and llm_label is None:
        raise ValueError("LLM configs need the LLM label")
    predicted = llm_label if kind is ConfigKind.LLM else classifier_label

    # 1. Any sensitive prediction from either model goes to a person.
    if classifier_label in params.sensitive_intents or llm_label in params.sensitive_intents:
        return Route.REVIEW
    # 2. The LLM says the request is outside the label catalog.
    if llm_label == OUT_OF_SCOPE:
        return Route.ABSTAIN
    # 5. Intents outside the eligible cohort never automate.
    if params.eligible_cohort is not None and predicted not in params.eligible_cohort:
        return Route.REVIEW
    # 3. Classifier config: calibrated probability meets the threshold.
    if kind is ConfigKind.CLASSIFIER and classifier_prob >= params.classifier_threshold:
        return Route.AUTO
    # 4. LLM config: the two models agree and the classifier clears a lower bar.
    if (
        kind is ConfigKind.LLM
        and params.agreement_threshold is not None
        and llm_label == classifier_label
        and classifier_prob >= params.agreement_threshold
    ):
        return Route.AUTO
    # 6. Everything else goes to review.
    return Route.REVIEW


@dataclass(frozen=True)
class ThresholdChoice:
    threshold: float
    dev_auto_precision: float
    dev_coverage: float
    dev_auto_count: int


def tune_classifier_threshold(
    labels: Sequence[str],
    probs: Sequence[float],
    references: Sequence[str],
    sensitive: frozenset[str],
    target_precision: float,
    min_auto: int = 50,
) -> ThresholdChoice:
    """Pick the threshold that maximizes coverage while auto precision stays at target.

    Runs on the development set only. Sensitive predictions never count as auto.
    """
    best: ThresholdChoice | None = None
    n = len(labels)
    for step in range(100):
        t = step / 100
        auto = [
            label == ref
            for label, p, ref in zip(labels, probs, references, strict=True)
            if label not in sensitive and p >= t
        ]
        if len(auto) < min_auto:
            continue
        precision = sum(auto) / len(auto)
        if precision < target_precision:
            continue
        choice = ThresholdChoice(t, precision, len(auto) / n, len(auto))
        if best is None or choice.dev_coverage > best.dev_coverage:
            best = choice
    if best is None:
        raise ValueError(f"no threshold reaches auto precision {target_precision} on dev")
    return best
