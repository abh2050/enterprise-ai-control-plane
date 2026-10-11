"""Release scorecard (Section 6.5).

Every value is returned as a ``Metric`` carrying the provenance of the run it came from.
Definitions:
- Macro F1 is computed over the 77 Banking77 labels. An abstention counts as a miss: it
  is a false negative for the true label and a false positive for no label.
- Sensitive recall is label recall for each sensitive intent.
- Auto precision is the share of auto-routed cases whose label is correct.
- Latency percentiles use the nearest-rank method.
- A case is "correctly handled" unless it was auto-routed with the wrong label.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from control_plane.contracts import Metric, Provenance, Route
from control_plane.settings import MICROS_PER_USD

ABSTAIN_LABEL = "__abstain__"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    reference_label: str
    predicted_label: str | None  # None when the route is abstain
    route: Route
    latency_ms: int
    cost_micros: int

    @property
    def correct(self) -> bool:
        return self.route is not Route.ABSTAIN and self.predicted_label == self.reference_label


@dataclass(frozen=True)
class RiskResult:
    case_id: str
    category: str
    expected_route: Route
    route: Route


@dataclass(frozen=True)
class Economics:
    """Assumed per-case costs from configs/business_model.yaml (ASSUMPTION)."""

    review_cost_usd: float
    misroute_cost_standard_usd: float
    misroute_cost_sensitive_usd: float


def macro_f1(results: Sequence[CaseResult], labels: Sequence[str]) -> float:
    tp = dict.fromkeys(labels, 0)
    fp = dict.fromkeys(labels, 0)
    fn = dict.fromkeys(labels, 0)
    for r in results:
        pred = r.predicted_label if r.route is not Route.ABSTAIN else ABSTAIN_LABEL
        if pred == r.reference_label:
            tp[r.reference_label] += 1
            continue
        fn[r.reference_label] += 1
        if pred in fp:
            fp[pred] += 1
    scores = []
    for label in labels:
        denom = 2 * tp[label] + fp[label] + fn[label]
        scores.append(2 * tp[label] / denom if denom else 0.0)
    return sum(scores) / len(scores)


def auto_precision(results: Sequence[CaseResult]) -> float | None:
    auto = [r for r in results if r.route is Route.AUTO]
    return sum(r.correct for r in auto) / len(auto) if auto else None


def nearest_rank(values: Sequence[float], pct: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def total_cost_per_correct(
    results: Sequence[CaseResult], econ: Economics, sensitive: frozenset[str]
) -> float | None:
    model_usd = sum(r.cost_micros for r in results) / MICROS_PER_USD
    review_usd = sum(r.route is not Route.AUTO for r in results) * econ.review_cost_usd
    misroute_usd = 0.0
    handled = 0
    for r in results:
        if r.route is Route.AUTO and not r.correct:
            misroute_usd += (
                econ.misroute_cost_sensitive_usd
                if r.reference_label in sensitive
                else econ.misroute_cost_standard_usd
            )
        else:
            handled += 1
    if not handled:
        return None
    return (model_usd + review_usd + misroute_usd) / handled


def paired_bootstrap(
    baseline: Sequence[CaseResult],
    candidate: Sequence[CaseResult],
    stat: Callable[[Sequence[CaseResult]], float | None],
    resamples: int = 1000,
    seed: int = 42,
) -> tuple[float | None, float | None, float | None]:
    """Candidate minus baseline, with a 95% percentile interval over paired resamples."""
    base_by_id = {r.case_id: r for r in baseline}
    cand_by_id = {r.case_id: r for r in candidate}
    if base_by_id.keys() != cand_by_id.keys():
        raise ValueError("paired bootstrap needs identical cases")
    ids = sorted(base_by_id)
    b = [base_by_id[i] for i in ids]
    c = [cand_by_id[i] for i in ids]
    point_b, point_c = stat(b), stat(c)
    point = None if point_b is None or point_c is None else point_c - point_b
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(resamples):
        idx = rng.integers(0, len(ids), len(ids))
        sb = stat([b[i] for i in idx])
        sc = stat([c[i] for i in idx])
        if sb is not None and sc is not None:
            deltas.append(sc - sb)
    if not deltas:
        return point, None, None
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return point, float(lo), float(hi)


def build_scorecard(
    results: Sequence[CaseResult],
    labels: Sequence[str],
    sensitive: frozenset[str],
    risk: Sequence[RiskResult],
    provenance: Provenance,
    source: str,
    economics: Economics | None = None,
) -> dict[str, Metric]:
    n = len(results)

    def m(value: float | None, unit: str, prov: Provenance = provenance) -> Metric:
        return Metric(value=value, unit=unit, provenance=prov, source=source)

    card: dict[str, Metric] = {
        "cases": m(n, "cases"),
        "macro_f1": m(macro_f1(results, labels), "ratio"),
        "accuracy": m(sum(r.correct for r in results) / n, "ratio"),
        "automation_coverage": m(sum(r.route is Route.AUTO for r in results) / n, "ratio"),
        "auto_precision": m(auto_precision(results), "ratio"),
        "review_rate": m(sum(r.route is Route.REVIEW for r in results) / n, "ratio"),
        "abstention_rate": m(sum(r.route is Route.ABSTAIN for r in results) / n, "ratio"),
        "latency_p50_ms": m(nearest_rank([r.latency_ms for r in results], 50), "ms"),
        "latency_p95_ms": m(nearest_rank([r.latency_ms for r in results], 95), "ms"),
        "model_cost_per_1k_usd": m(
            sum(r.cost_micros for r in results) / n * 1000 / MICROS_PER_USD, "USD per 1,000 cases"
        ),
        # Mixes measured model cost with assumed review and misroute costs.
        "total_cost_per_correct_usd": m(
            total_cost_per_correct(results, economics, sensitive) if economics else None,
            "USD per correctly handled case",
            Provenance.ASSUMPTION if provenance is Provenance.MEASURED else provenance,
        ),
    }
    for intent in sorted(sensitive):
        cases = [r for r in results if r.reference_label == intent]
        recall = sum(r.predicted_label == intent for r in cases) / len(cases) if cases else None
        card[f"sensitive_recall.{intent}"] = m(recall, "ratio")
        routed = sum(r.route is Route.REVIEW for r in cases) / len(cases) if cases else None
        card[f"sensitive_review_rate.{intent}"] = m(routed, "ratio")
    for category in sorted({r.category for r in risk}):
        items = [r for r in risk if r.category == category]
        accuracy = sum(r.route is r.expected_route for r in items) / len(items)
        card[f"risk_route_accuracy.{category}"] = m(accuracy, "ratio")
    return card
