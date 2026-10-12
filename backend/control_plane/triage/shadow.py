"""Shadow deployment replay (Section 6.6). Every shadow metric is SIMULATED.

For each of the 14 simulated days, the approved config (classifier_v1) produces the
authoritative route. The candidate runs on the same case through the budget ledger and
its output is stored only for comparison. Comparisons record agreement, both routes,
both labels, both costs, and what the proposed cohort would have done. Case text never
enters the committed artifacts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from control_plane.contracts import ConfigKind, Route
from control_plane.pricing import load_price_card
from control_plane.providers.base import Provider
from control_plane.settings import Settings
from control_plane.store import Store
from control_plane.triage import classifier as clf_mod
from control_plane.triage.business_model import load_assumptions
from control_plane.triage.dataset import REPO_ROOT, SENSITIVE_INTENTS, Case, load_split, shadow_days
from control_plane.triage.evaluate import CONFIG_DIR, POLICY_DIR, _policy_params, _read
from control_plane.triage.llm_eval import LLMCall, llm_context, run_llm_calls
from control_plane.triage.policy import route
from control_plane.triage.scorecard import CaseResult

SHADOW_DIR = REPO_ROOT / "artifacts" / "shadow"
APPROVED = "classifier_v1"


def _classifier() -> clf_mod.Classifier:
    record = _read(clf_mod.MODEL_DIR / "classifier_v1.json")
    return clf_mod.load("classifier_v1", record["model_sha256"])


def case_economics(result: CaseResult, a: Any) -> dict[str, float]:
    """Per-case contribution to net value (ASSUMPTION), mirroring business_model."""
    labor_saved = misroute = review = 0.0
    if result.route is Route.AUTO:
        if result.correct:
            labor_saved = a.manual_cost_per_case
        else:
            misroute = (
                a.misroute_cost_sensitive
                if result.reference_label in SENSITIVE_INTENTS
                else a.misroute_cost_standard
            )
    elif result.route is Route.REVIEW:
        review = a.review_cost_per_case
    model = result.cost_micros / 1e6
    return {
        "labor_saved": labor_saved,
        "misroute": misroute,
        "review": review,
        "model": model,
        "net": labor_saved - misroute - review - model,
    }


def compare(
    cases: list[tuple[int, Case]],
    calls: list[LLMCall],
    clf: clf_mod.Classifier,
    cand_params: Any,
    appr_params: Any,
    cohort: set[str],
) -> list[dict[str, Any]]:
    assumptions, _ = load_assumptions()
    preds = clf.predict([c.text for _, c in cases])
    rows = []
    for (day, case), call, pred in zip(cases, calls, preds, strict=True):
        a_route = route(appr_params, ConfigKind.CLASSIFIER, pred.label, pred.prob)
        c_route = (
            Route.REVIEW
            if call.llm_label is None
            else route(cand_params, ConfigKind.LLM, pred.label, pred.prob, call.llm_label)
        )
        c_label = call.llm_label if c_route is not Route.ABSTAIN else None
        approved = CaseResult(case.case_id, case.label, pred.label, a_route, 2, 0)
        candidate = CaseResult(
            case.case_id, case.label, c_label, c_route, call.latency_ms, call.cost_micros
        )
        in_cohort = pred.label in cohort
        cohort_result = candidate if in_cohort else approved
        rows.append(
            {
                "day": day,
                "case_id": case.case_id,
                "reference_label": case.label,
                "approved_label": pred.label,
                "approved_prob": round(pred.prob, 6),
                "approved_route": a_route.value,
                "candidate_label": call.llm_label,
                "candidate_route": c_route.value,
                "candidate_status": call.status,
                "label_agree": call.llm_label == pred.label,
                "route_agree": c_route is a_route,
                "approved_correct": approved.correct,
                "candidate_correct": candidate.correct,
                "candidate_cost_micros": call.cost_micros,
                "candidate_latency_ms": call.latency_ms,
                "in_cohort": in_cohort,
                "cohort_route": cohort_result.route.value,
                "cohort_correct": cohort_result.correct,
                "economics": {
                    "approved": case_economics(approved, assumptions),
                    "candidate": case_economics(candidate, assumptions),
                    "cohort": case_economics(cohort_result, assumptions),
                },
            }
        )
    return rows


def summarize_day(day: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)

    def routes(key: str) -> dict[str, int]:
        return {r: sum(x[key] == r for x in rows) for r in ("auto", "review", "abstain")}

    def money(config: str, part: str) -> float:
        return round(float(sum(x["economics"][config][part] for x in rows)), 4)

    return {
        "day": day,
        "cases": n,
        "label_agreement": sum(x["label_agree"] for x in rows) / n,
        "route_agreement": sum(x["route_agree"] for x in rows) / n,
        "routes": {
            "approved": routes("approved_route"),
            "candidate": routes("candidate_route"),
            "cohort": routes("cohort_route"),
        },
        "accuracy": {
            "approved": sum(x["approved_correct"] for x in rows) / n,
            "candidate": sum(x["candidate_correct"] for x in rows) / n,
            "cohort": sum(x["cohort_correct"] for x in rows) / n,
        },
        "candidate_cost_usd": sum(x["candidate_cost_micros"] for x in rows) / 1e6,
        "net_value_usd": {c: money(c, "net") for c in ("approved", "candidate", "cohort")},
        "provenance": "SIMULATED",
    }


def run_shadow(
    candidate_id: str,
    cohort: list[str],
    *,
    provider: Provider,
    store: Store,
    settings: Settings,
    progress: Callable[[int, int, LLMCall], None] | None = None,
) -> dict[str, Any]:
    config = _read(CONFIG_DIR / f"{candidate_id}.json")
    ctx = llm_context(candidate_id, settings)
    if ctx.static_prompt != config["prompt_text"]:
        raise RuntimeError("candidate prompt differs from its frozen config")
    cand_params = _policy_params(_read(POLICY_DIR / f"{config['policy_id']}.json"))
    appr_params = _policy_params(_read(POLICY_DIR / "policy_classifier_v1.json"))
    pool = {c.case_id: c for c in load_split("shadow_pool")}
    cases = [(i + 1, pool[cid]) for i, day in enumerate(shadow_days()) for cid in day]
    run_id = f"shadow_{candidate_id}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    card = load_price_card(config["price_card"])
    calls = run_llm_calls(
        ctx,
        [(c.case_id, c.text) for _, c in cases],
        experiment_id=run_id,
        provider=provider,
        price_card=card,
        store=store,
        settings=settings,
        progress=progress,
    )
    rows = compare(cases, calls, _classifier(), cand_params, appr_params, set(cohort))
    days = [summarize_day(d, [r for r in rows if r["day"] == d]) for d in range(1, 15)]
    out = SHADOW_DIR / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparisons.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    totals = {
        "cases": len(rows),
        "label_agreement": sum(r["label_agree"] for r in rows) / len(rows),
        "route_agreement": sum(r["route_agree"] for r in rows) / len(rows),
        "candidate_cost_usd": sum(r["candidate_cost_micros"] for r in rows) / 1e6,
        "net_value_usd": {
            c: round(sum(d["net_value_usd"][c] for d in days), 2)
            for c in ("approved", "candidate", "cohort")
        },
        "accuracy": {
            c: sum(r[f"{c}_correct"] for r in rows) / len(rows)
            for c in ("approved", "candidate", "cohort")
        },
        "unknown_outcomes": sum(c.status == "unknown" for c in calls),
        "fresh_calls": sum(not c.from_cache for c in calls),
    }
    summary = {
        "run_id": run_id,
        "authoritative_config_id": APPROVED,
        "candidate_config_id": candidate_id,
        "cohort": cohort,
        "simulated_days": 14,
        "days": days,
        "totals": totals,
        "price_card": card.version,
        "backend": provider.backend,
        "provenance": "SIMULATED",
        "note": "Shadow traffic replays the Banking77 shadow pool in 14 simulated days. Net "
        "value uses ASSUMPTION inputs from configs/business_model.yaml.",
        "finished_at": datetime.now(UTC).isoformat(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
