"""LLM config experiments: dev tuning, freezing, frozen evaluation, and the pilot.

Every model call goes through the budget ledger (``call_with_budget``) unless the same
prompt already has a completed response in the local cache. Runs are resumable: if the
service rate-limits a case twice, the run stops, and the next invocation continues the
same experiment from the cache. Experiment records name the backend and price card.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from control_plane.budget import BudgetLimits, CallOutcome, Ledger, call_with_budget
from control_plane.contracts import AttemptStatus, ConfigKind, Limits, Route
from control_plane.pricing import PriceCard, load_price_card
from control_plane.providers.base import Provider
from control_plane.settings import Settings
from control_plane.store import Store
from control_plane.triage import classifier as clf_mod
from control_plane.triage.dataset import (
    SENSITIVE_INTENTS,
    Case,
    load_categories,
    load_manifest,
    load_split,
)
from control_plane.triage.evaluate import (
    APP_ID,
    CONFIG_DIR,
    EXPERIMENT_DIR,
    FROZEN_RUNS,
    POLICY_DIR,
    FreezeError,
    _policy_params,
    _read,
    _write_create_only,
    frozen_case_order,
    load_risk_suite,
    triage_settings,
)
from control_plane.triage.llm import (
    RateLimiter,
    ResponseCache,
    build_prompt,
    build_static_prompt,
    cache_key,
    parse_intent,
    pick_examples,
    prompt_sha256,
    response_schema,
)
from control_plane.triage.policy import route
from control_plane.triage.scorecard import CaseResult, RiskResult, build_scorecard

REJECTION_BACKOFF_SECONDS = 20.0


class RunPausedError(RuntimeError):
    """The service kept refusing requests; resume later and the run continues."""


@dataclass
class LLMContext:
    config_id: str
    spec: dict[str, Any]
    model_id: str
    limits: Limits
    static_prompt: str
    schema: dict[str, Any]
    categories: list[str]
    tuning_cases: list[Case]


def llm_context(config_id: str, settings: Settings) -> LLMContext:
    spec = triage_settings()["configs"][config_id]
    if spec["kind"] != ConfigKind.LLM.value:
        raise FreezeError(f"{config_id} is not an LLM config")
    model_id = getattr(settings, spec["model_setting"])
    categories = load_categories()
    dev = load_split("dev")
    examples = pick_examples(dev, spec["examples_per_label"])
    frozen_texts = [c.text for c in load_split("frozen_eval")]
    static = build_static_prompt(categories, examples, frozen_texts)
    example_ids = {e.case_id for e in examples}
    limits = Limits(
        max_input_tokens=8_000,
        max_output_tokens=spec["max_output_tokens"],
        deadline_seconds=30,
        max_attempts_per_case=2,
    )
    return LLMContext(
        config_id=config_id,
        spec=spec,
        model_id=model_id,
        limits=limits,
        static_prompt=static,
        schema=response_schema(categories),
        categories=categories,
        # Dev rows used as prompt examples are excluded from tuning.
        tuning_cases=[c for c in dev if c.case_id not in example_ids],
    )


def _ledger(store: Store, settings: Settings) -> Ledger:
    return Ledger(
        store,
        BudgetLimits(
            app_daily_micros=settings.budget_app_daily_micros,
            experiment_micros=settings.budget_experiment_micros,
            total_micros=settings.budget_experiment_total_micros,
        ),
    )


@dataclass(frozen=True)
class LLMCall:
    case_id: str
    llm_label: str | None
    status: str  # completed, unknown, or failed
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    cached_tokens: int
    cost_micros: int
    latency_ms: int
    attempt_count: int
    finish_reason: str | None
    from_cache: bool


def run_llm_calls(
    ctx: LLMContext,
    cases: list[tuple[str, str]],  # (case_id, text)
    *,
    experiment_id: str,
    provider: Provider,
    price_card: PriceCard,
    store: Store,
    settings: Settings,
    progress: Callable[[int, int, LLMCall], None] | None = None,
) -> list[LLMCall]:
    """Call the model once per case through the ledger, or reuse a cached response."""
    ledger = _ledger(store, settings)
    price = price_card.price(ctx.model_id)
    cache = ResponseCache()
    limiter = RateLimiter(settings.llm_requests_per_minute)
    gen_settings = {
        "max_output_tokens": ctx.limits.max_output_tokens,
        "thinking_level": ctx.spec["thinking_level"],
        "temperature": 0,
    }
    calls: list[LLMCall] = []
    for i, (case_id, text) in enumerate(cases):
        prompt = build_prompt(ctx.static_prompt, text)
        key = cache_key(provider.backend, ctx.model_id, prompt, ctx.schema, gen_settings)
        cached = cache.get(key)
        if cached is not None:
            call = LLMCall(**{**cached["call"], "case_id": case_id, "from_cache": True})
        else:
            call = _fresh_call(
                ctx, case_id, prompt, experiment_id, provider, price, ledger, limiter
            )
            if call.status == AttemptStatus.COMPLETED.value:
                cache.put(key, {"call": {**call.__dict__}, "price_card": price_card.version})
        calls.append(call)
        if progress:
            progress(i + 1, len(cases), call)
    return calls


def _fresh_call(
    ctx: LLMContext,
    case_id: str,
    prompt: str,
    experiment_id: str,
    provider: Provider,
    price: Any,
    ledger: Ledger,
    limiter: RateLimiter,
) -> LLMCall:
    outcome: CallOutcome | None = None
    attempts = 0
    for attempt in range(ctx.limits.max_attempts_per_case):
        if attempt:
            time.sleep(REJECTION_BACKOFF_SECONDS)
        limiter.wait()
        attempts += 1
        outcome = call_with_budget(
            ledger,
            provider,
            price,
            ctx.limits,
            app_id=APP_ID,
            experiment_id=experiment_id,
            case_id=case_id,
            model_id=ctx.model_id,
            prompt=prompt,
            response_schema=ctx.schema,
        )
        # Only a refusal before processing may be tried again. Unknown never retries.
        if outcome.status is not AttemptStatus.FAILED:
            break
    assert outcome is not None
    if outcome.status is AttemptStatus.FAILED:
        raise RunPausedError(
            f"{case_id}: refused twice ({outcome.failure_reason}). Re-run the same command "
            "later; completed cases come from the cache."
        )
    resp = outcome.response
    return LLMCall(
        case_id=case_id,
        llm_label=parse_intent(resp.output, ctx.categories) if resp else None,
        status=outcome.status.value,
        input_tokens=resp.input_tokens if resp else outcome.counted_input_tokens,
        output_tokens=resp.output_tokens if resp else 0,
        thinking_tokens=resp.thinking_tokens if resp else 0,
        cached_tokens=resp.cached_tokens if resp else 0,
        cost_micros=outcome.actual_micros or 0,
        latency_ms=resp.latency_ms if resp else ctx.limits.deadline_seconds * 1000,
        attempt_count=attempts,
        finish_reason=resp.finish_reason if resp else None,
        from_cache=False,
    )


def _classifier() -> clf_mod.Classifier:
    record = _read(clf_mod.MODEL_DIR / "classifier_v1.json")
    return clf_mod.load("classifier_v1", record["model_sha256"])


# Pilot and dev tuning


def pilot(
    config_id: str,
    n: int,
    *,
    provider: Provider,
    store: Store,
    settings: Settings,
    progress: Callable[[int, int, LLMCall], None] | None = None,
) -> dict[str, Any]:
    """Run the first ``n`` tuning cases (dev only) and project the cost of the full plan."""
    ctx = llm_context(config_id, settings)
    card = load_price_card()
    cases = [(c.case_id, c.text) for c in ctx.tuning_cases[:n]]
    calls = run_llm_calls(
        ctx,
        cases,
        experiment_id=f"dev_{config_id}",
        provider=provider,
        price_card=card,
        store=store,
        settings=settings,
        progress=progress,
    )
    done = [c for c in calls if c.status == "completed"]
    price = card.price(ctx.model_id)
    mean = {
        k: sum(getattr(c, k) for c in done) / max(1, len(done))
        for k in ("input_tokens", "output_tokens", "thinking_tokens", "cached_tokens", "latency_ms")
    }
    per_call_micros = price.cost_micros(
        round(mean["input_tokens"]), round(mean["output_tokens"]), round(mean["cached_tokens"])
    )
    planned = len(ctx.tuning_cases) + len(load_split("frozen_eval")) + len(load_risk_suite())
    return {
        "config_id": config_id,
        "model_id": ctx.model_id,
        "backend": provider.backend,
        "price_card": card.version,
        "cases": len(calls),
        "completed": len(done),
        "valid_labels": sum(c.llm_label is not None for c in done),
        "mean": mean,
        "cost_per_call_usd_list_price": per_call_micros / 1e6,
        "planned_calls_for_m3": planned,
        "projected_m3_cost_usd_list_price": per_call_micros * planned / 1e6,
        "finish_reasons": sorted({str(c.finish_reason) for c in done}),
    }


def tune_and_freeze(
    config_id: str,
    *,
    provider: Provider,
    store: Store,
    settings: Settings,
    progress: Callable[[int, int, LLMCall], None] | None = None,
) -> dict[str, Any]:
    """Tune the agreement threshold on dev (examples excluded), then freeze."""
    ctx = llm_context(config_id, settings)
    card = load_price_card()
    tuning = triage_settings()["policy_tuning"]
    calls = run_llm_calls(
        ctx,
        [(c.case_id, c.text) for c in ctx.tuning_cases],
        experiment_id=f"dev_{config_id}",
        provider=provider,
        price_card=card,
        store=store,
        settings=settings,
        progress=progress,
    )
    clf = _classifier()
    preds = clf.predict([c.text for c in ctx.tuning_cases])
    base_policy = _read(POLICY_DIR / "policy_classifier_v1.json")
    sensitive = frozenset(base_policy["sensitive_intents"])
    target = tuning["target_dev_auto_precision"]["value"]
    min_auto = tuning["min_dev_auto_cases"]["value"]
    n = len(ctx.tuning_cases)
    best: dict[str, Any] | None = None
    for step in range(100):
        t = step / 100
        auto = [
            call.llm_label == case.label
            for case, call, pred in zip(ctx.tuning_cases, calls, preds, strict=True)
            if call.llm_label is not None
            and call.llm_label not in sensitive
            and pred.label not in sensitive
            and call.llm_label == pred.label
            and pred.prob >= t
        ]
        if len(auto) < min_auto:
            continue
        precision = sum(auto) / len(auto)
        if precision >= target and (best is None or len(auto) / n > best["dev_coverage"]):
            best = {
                "threshold": t,
                "dev_auto_precision": precision,
                "dev_coverage": len(auto) / n,
                "dev_auto_count": len(auto),
            }
    if best is None:
        raise FreezeError(f"no agreement threshold reaches {target} dev auto precision")
    dev_accuracy = (
        sum(c.llm_label == k.label for c, k in zip(calls, ctx.tuning_cases, strict=True)) / n
    )
    policy_id = ctx.spec["policy_id"]
    now = datetime.now(UTC).isoformat()
    policy = {
        "policy_id": policy_id,
        "thresholds": {
            "classifier_threshold": base_policy["thresholds"]["classifier_threshold"],
            "agreement_threshold": best["threshold"],
        },
        "sensitive_intents": base_policy["sensitive_intents"],
        "eligible_cohort": base_policy["eligible_cohort"],
        "tuning": {
            "split": "dev minus prompt examples",
            "rows": n,
            "target_dev_auto_precision": tuning["target_dev_auto_precision"],
            "dev_llm_accuracy": dev_accuracy,
            **{k: best[k] for k in ("dev_auto_precision", "dev_coverage", "dev_auto_count")},
        },
        "created_at": now,
    }
    config = {
        "config_id": config_id,
        "app_id": APP_ID,
        "version": ctx.spec["version"],
        "kind": ConfigKind.LLM.value,
        "model_id": ctx.model_id,
        "backend": provider.backend,
        "prompt_text": ctx.static_prompt,
        "prompt_sha256": prompt_sha256(ctx.static_prompt),
        "policy_id": policy_id,
        "limits": ctx.limits.model_dump(),
        "generation": {"temperature": 0, "thinking_level": ctx.spec["thinking_level"]},
        "price_card": card.version,
        "created_by": "cli",
        "created_at": now,
    }
    _write_create_only(POLICY_DIR / f"{policy_id}.json", policy)
    _write_create_only(CONFIG_DIR / f"{config_id}.json", config)
    return {"policy": policy, "config": config}


# Frozen evaluation


def evaluate_llm_config(
    config_id: str,
    *,
    provider: Provider,
    store: Store,
    settings: Settings,
    rerun_reason: str | None = None,
    progress: Callable[[int, int, LLMCall], None] | None = None,
) -> dict[str, Any]:
    config_path = CONFIG_DIR / f"{config_id}.json"
    if not config_path.exists():
        raise FreezeError(f"{config_id} is not frozen yet; run `cp tune {config_id}`")
    config = _read(config_path)
    if config["backend"] != provider.backend:
        raise FreezeError(f"{config_id} was frozen on {config['backend']}, not {provider.backend}")
    policy = _read(POLICY_DIR / f"{config['policy_id']}.json")
    params = _policy_params(policy)
    ctx = llm_context(config_id, settings)
    if ctx.static_prompt != config["prompt_text"]:
        raise FreezeError("prompt differs from the frozen config")
    card = load_price_card(config["price_card"])

    runs: dict[str, Any] = _read(FROZEN_RUNS) if FROZEN_RUNS.exists() else {}
    prior = runs.get(config_id)
    if prior and prior.get("status", "finished") == "finished" and not rerun_reason:
        raise FreezeError(f"{config_id} already ran on the frozen set ({prior['experiment_id']}).")
    if prior and prior.get("status") == "running":
        experiment_id = prior["experiment_id"]  # resume the interrupted run
    else:
        experiment_id = f"exp_{config_id}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        history = (prior or {}).get("history", [])
        runs[config_id] = {
            "experiment_id": experiment_id,
            "status": "running",
            "history": history,
            "started_at": datetime.now(UTC).isoformat(),
        }
        FROZEN_RUNS.write_text(json.dumps(runs, indent=2) + "\n")

    cases = frozen_case_order(load_split("frozen_eval"))
    risk = load_risk_suite()
    calls = run_llm_calls(
        ctx,
        [(c.case_id, c.text) for c in cases] + [(r["case_id"], r["text"]) for r in risk],
        experiment_id=experiment_id,
        provider=provider,
        price_card=card,
        store=store,
        settings=settings,
        progress=progress,
    )
    clf = _classifier()
    frozen_calls = calls[: len(cases)]
    risk_calls = calls[len(cases) :]

    rows, results = [], []
    clf_preds = clf.predict([c.text for c in cases])
    for case, call, pred in zip(cases, frozen_calls, clf_preds, strict=True):
        r = _route(params, pred.label, pred.prob, call.llm_label)
        predicted = call.llm_label if r is not Route.ABSTAIN else None
        result = CaseResult(
            case.case_id, case.label, predicted, r, call.latency_ms, call.cost_micros
        )
        results.append(result)
        rows.append(
            {
                "case_id": case.case_id,
                "predicted_label": predicted,
                "reference_label": case.label,
                "route": r.value,
                "correct": result.correct,
                "classifier_label": pred.label,
                "classifier_prob": round(pred.prob, 6),
                "llm_status": call.status,
                "latency_ms": call.latency_ms,
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "thinking_tokens": call.thinking_tokens,
                "cached_tokens": call.cached_tokens,
                "cost_micros": call.cost_micros,
                "attempt_count": call.attempt_count,
                "finish_reason": call.finish_reason,
            }
        )
    risk_rows, risk_results = [], []
    risk_preds = clf.predict([r["text"] for r in risk])
    for item, call, pred in zip(risk, risk_calls, risk_preds, strict=True):
        r = _route(params, pred.label, pred.prob, call.llm_label)
        expected = Route(item["expected_route"])
        risk_results.append(RiskResult(item["case_id"], item["category"], expected, r))
        risk_rows.append(
            {
                "case_id": item["case_id"],
                "category": item["category"],
                "expected_route": expected.value,
                "route": r.value,
                "llm_label": call.llm_label,
                "classifier_label": pred.label,
            }
        )

    source = f"artifacts/experiments/{experiment_id}/results.jsonl"
    card_metrics = build_scorecard(
        results,
        ctx.categories,
        frozenset(SENSITIVE_INTENTS),
        risk_results,
        provider.provenance,
        source,
    )
    out = EXPERIMENT_DIR / experiment_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "risk_results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in risk_rows))
    (out / "scorecard.json").write_text(
        json.dumps({k: v.model_dump() for k, v in card_metrics.items()}, indent=2) + "\n"
    )
    usage = {
        "calls": len(calls),
        "fresh_calls": sum(not c.from_cache for c in calls),
        "unknown_outcomes": sum(c.status == "unknown" for c in calls),
        "invalid_outputs": sum(c.status == "completed" and c.llm_label is None for c in calls),
        "cost_micros_list_price": sum(c.cost_micros for c in calls),
        "input_tokens": sum(c.input_tokens for c in calls),
        "output_tokens": sum(c.output_tokens for c in calls),
        "thinking_tokens": sum(c.thinking_tokens for c in calls),
        "cached_tokens": sum(c.cached_tokens for c in calls),
    }
    experiment = {
        "experiment_id": experiment_id,
        "config_id": config_id,
        "policy_id": policy["policy_id"],
        "dataset_id": "banking77_frozen_eval",
        "dataset_sha256": load_manifest()["splits"]["frozen_eval"]["sha256"],
        "case_order_seed": 42,
        "status": "finished",
        "backend": provider.backend,
        "model_id": config["model_id"],
        "price_card": card.version,
        "billing_note": "Free-tier calls bill $0. cost_micros_list_price is the same usage "
        "at paid-tier list prices.",
        "usage": usage,
        "started_at": runs[config_id]["started_at"],
        "finished_at": datetime.now(UTC).isoformat(),
        "provenance": provider.provenance.value,
        "rerun_reason": rerun_reason,
    }
    (out / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")
    runs[config_id]["status"] = "finished"
    runs[config_id]["history"].append(
        {"experiment_id": experiment_id, "reason": rerun_reason or "first run"}
    )
    FROZEN_RUNS.write_text(json.dumps(runs, indent=2) + "\n")
    return {"experiment": experiment, "scorecard": card_metrics}


def _route(params: Any, clf_label: str, clf_prob: float, llm_label: str | None) -> Route:
    if llm_label is None:
        # No valid model answer: sensitive classifier labels still review; all else reviews.
        return Route.REVIEW
    return route(params, ConfigKind.LLM, clf_label, clf_prob, llm_label)
