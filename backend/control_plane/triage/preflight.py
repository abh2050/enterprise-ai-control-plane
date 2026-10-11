"""Preflight: verify model access, token counting, and structured output.

Live runs refuse to start unless a passing preflight for the same backend and model is
recorded in artifacts/preflight/. Each check makes one tiny call through the ledger.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from control_plane.budget import call_with_budget
from control_plane.contracts import AttemptStatus, Limits
from control_plane.pricing import load_price_card
from control_plane.providers.base import Provider
from control_plane.settings import Settings
from control_plane.store import Store
from control_plane.triage.evaluate import APP_ID, ARTIFACTS
from control_plane.triage.llm import parse_intent
from control_plane.triage.llm_eval import _ledger

PREFLIGHT_DIR = ARTIFACTS / "preflight"
MAX_AGE = timedelta(days=7)
PROBE_LABELS = ["card_arrival", "exchange_rate", "lost_or_stolen_card"]
PROBE_PROMPT = (
    "Route this banking support message to one intent from: "
    + ", ".join(PROBE_LABELS)
    + ', or "out_of_scope". Reply as JSON.\nMessage: "When will my new card get here?"'
)


def run_preflight(
    model_ids: list[str],
    *,
    provider: Provider,
    store: Store,
    settings: Settings,
    thinking_level: str,
) -> dict[str, Any]:
    card = load_price_card()
    ledger = _ledger(store, settings)
    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": [*PROBE_LABELS, "out_of_scope"]},
            "rationale": {"type": "string", "maxLength": 300},
        },
        "required": ["intent", "rationale"],
    }
    stamp = datetime.now(UTC)
    report: dict[str, Any] = {
        "backend": provider.backend,
        "checked_at": stamp.isoformat(),
        "price_card": card.version,
        "thinking_level": thinking_level,
        "models": {},
    }
    for model_id in model_ids:
        result: dict[str, Any] = {"model_id": model_id}
        try:
            result["count_tokens"] = provider.count_tokens(model_id, PROBE_PROMPT).input_tokens
            outcome = call_with_budget(
                ledger,
                provider,
                card.price(model_id),
                Limits(max_output_tokens=256),
                app_id=APP_ID,
                experiment_id=f"preflight_{stamp:%Y%m%dT%H%M%S}",
                case_id=model_id,
                model_id=model_id,
                prompt=PROBE_PROMPT,
                response_schema=schema,
            )
            resp = outcome.response
            intent = parse_intent(resp.output, PROBE_LABELS) if resp else None
            result.update(
                status=outcome.status.value,
                structured_output_valid=intent is not None,
                intent=intent,
                finish_reason=resp.finish_reason if resp else None,
                input_tokens=resp.input_tokens if resp else None,
                output_tokens=resp.output_tokens if resp else None,
                thinking_tokens=resp.thinking_tokens if resp else None,
                latency_ms=resp.latency_ms if resp else None,
                cost_usd_list_price=(outcome.actual_micros or 0) / 1e6,
            )
            result["passed"] = bool(
                outcome.status is AttemptStatus.COMPLETED
                and result["count_tokens"] > 0
                and intent is not None
                and result["finish_reason"] == "STOP"
            )
        except Exception as exc:  # report every failure; never pass silently
            result.update(passed=False, error=f"{type(exc).__name__}: {exc}")
        report["models"][model_id] = result
    report["passed"] = all(m["passed"] for m in report["models"].values())
    PREFLIGHT_DIR.mkdir(parents=True, exist_ok=True)
    path = PREFLIGHT_DIR / f"{stamp:%Y%m%dT%H%M%SZ}_{provider.backend}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    report["path"] = str(path)
    return report


def require_preflight(backend: str, model_id: str) -> None:
    for path in sorted(PREFLIGHT_DIR.glob(f"*_{backend}.json"), reverse=True):
        report = json.loads(path.read_text())
        checked = datetime.fromisoformat(report["checked_at"])
        if datetime.now(UTC) - checked > MAX_AGE:
            break
        if report["models"].get(model_id, {}).get("passed"):
            return
    raise RuntimeError(
        f"no passing preflight for {model_id} on {backend} in the last 7 days; run `cp preflight`"
    )
