"""Release gates (Section 6.5) and cohort blending (Section 6.7).

A cohort is a list of intents. For a case whose approved-config predicted intent is in
the cohort, the candidate config is authoritative; every other case stays on the
approved config. Gates evaluate any result set, including a blended cohort, and every
result stores its threshold, observed value, and pass or fail.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from control_plane.contracts import Route
from control_plane.triage.business_model import breakeven_precision, load_assumptions
from control_plane.triage.dataset import REPO_ROOT, SENSITIVE_INTENTS, load_categories
from control_plane.triage.evaluate import EXPERIMENT_DIR, FROZEN_RUNS
from control_plane.triage.report import rates_from
from control_plane.triage.scorecard import (
    CaseResult,
    RiskResult,
    auto_precision,
    build_scorecard,
    macro_f1,
    nearest_rank,
)

GATES_PATH = REPO_ROOT / "configs" / "release_gates.yaml"


def gate_config() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(GATES_PATH.read_text())
    return data


@dataclass(frozen=True)
class FrozenRun:
    config_id: str
    rows: list[dict[str, Any]]
    risk_rows: list[dict[str, Any]]


def load_frozen(config_id: str) -> FrozenRun:
    runs = json.loads(FROZEN_RUNS.read_text())
    exp = EXPERIMENT_DIR / runs[config_id]["experiment_id"]
    rows = [json.loads(x) for x in (exp / "results.jsonl").read_text().splitlines()]
    risk = [json.loads(x) for x in (exp / "risk_results.jsonl").read_text().splitlines()]
    return FrozenRun(config_id, rows, risk)


def _case(r: dict[str, Any]) -> CaseResult:
    return CaseResult(
        r["case_id"],
        r["reference_label"],
        r["predicted_label"],
        Route(r["route"]),
        r["latency_ms"],
        r["cost_micros"],
    )


def blend(
    approved: FrozenRun, candidate: FrozenRun, cohort: Iterable[str] | None
) -> tuple[list[CaseResult], list[RiskResult], list[dict[str, Any]]]:
    """Per-case results when the candidate is authoritative only inside ``cohort``.

    ``cohort=None`` means the full candidate. Routing keys on the approved config's
    predicted intent, which is known before the candidate runs.
    """
    members = None if cohort is None else set(cohort)
    cand = {r["case_id"]: r for r in candidate.rows}
    results, rows = [], []
    for a in approved.rows:
        use_candidate = members is None or a["predicted_label"] in members
        r = cand[a["case_id"]] if use_candidate else a
        results.append(_case(r))
        rows.append(
            {**r, "authority": candidate.config_id if use_candidate else approved.config_id}
        )
    cand_risk = {r["case_id"]: r for r in candidate.risk_rows}
    risk = []
    for a in approved.risk_rows:
        clf_label = a.get("predicted_label") or a.get("classifier_label")
        use_candidate = members is None or clf_label in members
        r = cand_risk[a["case_id"]] if use_candidate else a
        risk.append(
            RiskResult(r["case_id"], r["category"], Route(r["expected_route"]), Route(r["route"]))
        )
    return results, risk, rows


def evaluate_gates(
    results: list[CaseResult],
    risk: list[RiskResult],
    baseline: list[CaseResult],
    cohort: Iterable[str] | None,
) -> list[dict[str, Any]]:
    cfg = gate_config()["gates"]
    labels = load_categories()
    members = set(labels) if cohort is None else set(cohort)
    gates: list[dict[str, Any]] = []

    def add(
        gate: str, threshold: float, observed: float | None, passed: bool, comparison: str
    ) -> None:
        gates.append(
            {
                "gate": gate,
                "threshold": round(threshold, 6),
                "observed": None if observed is None else round(observed, 6),
                "passed": bool(passed),
                "comparison": comparison,
            }
        )

    for intent in sorted(SENSITIVE_INTENTS):
        if intent not in members:
            continue
        cases = [r for r in results if r.reference_label == intent]
        recall = sum(r.predicted_label == intent for r in cases) / len(cases) if cases else None
        add(
            f"sensitive_recall.{intent}",
            cfg["sensitive_recall"]["min"],
            recall,
            recall is not None and recall >= cfg["sensitive_recall"]["min"],
            ">=",
        )

    assumptions, _ = load_assumptions()
    be = breakeven_precision(assumptions, rates_from(results))
    ap = auto_precision(results)
    threshold = (be if be is not None else 1.0) + cfg["auto_precision"]["margin_over_breakeven"]
    add("auto_precision", threshold, ap, ap is not None and ap >= threshold, ">=")

    base_f1 = macro_f1(baseline, labels)
    f1 = macro_f1(results, labels)
    f1_min = base_f1 - cfg["macro_f1"]["max_drop_vs_baseline"]
    add("macro_f1", f1_min, f1, f1 >= f1_min, ">=")

    p95 = nearest_rank([r.latency_ms for r in results], 95)
    add(
        "latency_p95_ms",
        cfg["latency_p95_ms"]["max"],
        p95,
        p95 <= cfg["latency_p95_ms"]["max"],
        "<=",
    )

    sens = [r for r in risk if r.category == "sensitive_indirect"]
    acc = sum(r.route is r.expected_route for r in sens) / len(sens) if sens else None
    add(
        "risk_sensitive_route_accuracy",
        cfg["risk_sensitive_route_accuracy"]["min"],
        acc,
        acc is not None and acc >= cfg["risk_sensitive_route_accuracy"]["min"],
        ">=",
    )
    return gates


def propose_cohort(candidate: FrozenRun, eligible: Iterable[str]) -> dict[str, Any]:
    """Eligible intents minus the sensitive intents whose candidate recall fails the gate."""
    minimum = gate_config()["gates"]["sensitive_recall"]["min"]
    results = [_case(r) for r in candidate.rows]
    failing = []
    for intent in sorted(SENSITIVE_INTENTS):
        cases = [r for r in results if r.reference_label == intent]
        recall = sum(r.predicted_label == intent for r in cases) / len(cases)
        if recall < minimum:
            failing.append({"intent": intent, "recall": recall})
    excluded = {f["intent"] for f in failing}
    return {
        "cohort": sorted(i for i in eligible if i not in excluded),
        "excluded": failing,
        "rule": f"exclude sensitive intents with recall < {minimum}",
    }


def blended_scorecard(
    results: list[CaseResult], risk: list[RiskResult], source: str
) -> dict[str, Any]:
    from control_plane.contracts import Provenance

    card = build_scorecard(
        results, load_categories(), frozenset(SENSITIVE_INTENTS), risk, Provenance.MEASURED, source
    )
    return {k: v.model_dump() for k, v in card.items()}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
