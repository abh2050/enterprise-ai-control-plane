"""Budget ledger and bounded execution (Section 7).

Flow for every paid model call:
1. Count input tokens and compute a reservation at the versioned price card.
2. In one transaction, admit the reservation only if the app's daily budget, the
   experiment budget, and the total experiment allowance all have room, and the case
   has used fewer than two attempts. Otherwise block and record ``budget_exhausted``.
3. Mark the attempt sent immediately before the call.
4. On a response, settle the actual cost and release the reservation exactly once.
5. On a timeout or lost response after send, mark the attempt unknown and keep the
   reservation. Never retry automatically.
6. If the actual cost exceeds the reservation, settle it, pause the app, and open an
   incident.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from control_plane.contracts import AttemptStatus, IncidentStatus, Limits, Provenance
from control_plane.pricing import ModelPrice
from control_plane.providers.base import (
    CacheHandle,
    Provider,
    ProviderRejectedError,
    ProviderResponse,
    ProviderTimeoutError,
)
from control_plane.store import Store, Transaction

TOTAL_ALLOWANCE_ID = "allowance_total"


class LedgerError(RuntimeError):
    pass


class BudgetExhaustedError(LedgerError):
    pass


class AttemptsExhaustedError(LedgerError):
    pass


class InputTooLargeError(LedgerError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    app_daily_micros: int
    experiment_micros: int
    total_micros: int


def _now() -> datetime:
    return datetime.now(UTC)


class Ledger:
    def __init__(self, store: Store, limits: BudgetLimits, clock: Callable[[], datetime] = _now):
        self._store = store
        self._limits = limits
        self._clock = clock

    # Budget documents

    def _budget_specs(self, app_id: str, experiment_id: str) -> list[tuple[str, int]]:
        day = self._clock().strftime("%Y%m%d")
        return [
            (f"{app_id}_{day}", self._limits.app_daily_micros),
            (f"experiment_{experiment_id}", self._limits.experiment_micros),
            (TOTAL_ALLOWANCE_ID, self._limits.total_micros),
        ]

    @staticmethod
    def _budget(tx: Transaction, budget_id: str, limit: int) -> dict[str, Any]:
        """Read a budget document. The configured limit is the source of truth, so a
        changed limit applies to the next reservation."""
        doc = tx.get("budgets", budget_id)
        if doc is None:
            doc = {
                "budget_id": budget_id,
                "limit_usd_micros": limit,
                "committed_micros": 0,
                "reserved_micros": 0,
            }
        doc["limit_usd_micros"] = limit
        return doc

    # 2. Reserve

    def reserve(
        self,
        *,
        app_id: str,
        experiment_id: str,
        case_id: str,
        model_id: str,
        reservation_micros: int,
        max_attempts: int,
    ) -> str:
        if reservation_micros <= 0:
            raise LedgerError("reservation must be positive")
        attempt_id = uuid.uuid4().hex
        specs = self._budget_specs(app_id, experiment_id)
        counter_id = f"{experiment_id}__{case_id}"
        now = self._clock().isoformat()

        def admit(tx: Transaction) -> str | None:
            budgets = [self._budget(tx, bid, limit) for bid, limit in specs]
            counter = tx.get("case_attempts", counter_id) or {"count": 0}
            if counter["count"] >= max_attempts:
                return "attempts_exhausted"
            for b in budgets:
                used = b["committed_micros"] + b["reserved_micros"]
                if used + reservation_micros > b["limit_usd_micros"]:
                    return f"budget_exhausted:{b['budget_id']}"
            for b in budgets:
                b["reserved_micros"] += reservation_micros
                tx.set("budgets", b["budget_id"], b)
            tx.set("case_attempts", counter_id, {"count": counter["count"] + 1})
            tx.create(
                "attempts",
                attempt_id,
                {
                    "attempt_id": attempt_id,
                    "app_id": app_id,
                    "experiment_id": experiment_id,
                    "case_id": case_id,
                    "model_id": model_id,
                    "status": AttemptStatus.RESERVED.value,
                    "reserved_micros": reservation_micros,
                    "budget_ids": [bid for bid, _ in specs],
                    "actual_micros": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cached_tokens": None,
                    "failure_reason": None,
                    "created_at": now,
                },
            )
            return None

        blocked = self._store.run_transaction(admit)
        if blocked:
            self._store.create(
                "budget_events",
                uuid.uuid4().hex,
                {
                    "kind": "budget_exhausted" if blocked.startswith("budget") else blocked,
                    "detail": blocked,
                    "app_id": app_id,
                    "experiment_id": experiment_id,
                    "case_id": case_id,
                    "reservation_micros": reservation_micros,
                    "created_at": now,
                },
            )
            if blocked == "attempts_exhausted":
                raise AttemptsExhaustedError(f"{case_id} used {max_attempts} attempts")
            raise BudgetExhaustedError(blocked)
        return attempt_id

    # 3. Send

    def mark_sent(self, attempt_id: str) -> None:
        def go(tx: Transaction) -> None:
            attempt = self._attempt(tx, attempt_id)
            if attempt["status"] != AttemptStatus.RESERVED.value:
                raise LedgerError(f"attempt {attempt_id} is {attempt['status']}, not reserved")
            tx.update("attempts", attempt_id, {"status": AttemptStatus.SENT.value})

        self._store.run_transaction(go)

    # 4. Settle

    def settle(
        self,
        attempt_id: str,
        *,
        actual_micros: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> bool:
        """Record the actual cost. Returns True if this call settled it, False if it was
        already settled (repeated settlement changes nothing)."""

        def go(tx: Transaction) -> tuple[bool, dict[str, Any]]:
            attempt = self._attempt(tx, attempt_id)
            if attempt["status"] == AttemptStatus.COMPLETED.value:
                return False, attempt
            if attempt["status"] not in (AttemptStatus.SENT.value, AttemptStatus.UNKNOWN.value):
                raise LedgerError(f"cannot settle attempt in status {attempt['status']}")
            budgets = [tx.get("budgets", bid) for bid in attempt["budget_ids"]]
            for b in budgets:
                if b is None:
                    raise LedgerError("budget document missing")
                b["reserved_micros"] -= attempt["reserved_micros"]
                b["committed_micros"] += actual_micros
                tx.set("budgets", b["budget_id"], b)
            tx.update(
                "attempts",
                attempt_id,
                {
                    "status": AttemptStatus.COMPLETED.value,
                    "actual_micros": actual_micros,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cached_tokens": cached_tokens,
                },
            )
            return True, attempt

        settled, attempt = self._store.run_transaction(go)
        if settled and actual_micros > attempt["reserved_micros"]:
            self._overrun(attempt, actual_micros)
        return settled

    # 5. Unknown outcome, and refusals before processing

    def mark_unknown(self, attempt_id: str, reason: str) -> None:
        """Keep the reservation: the call may still be billed."""

        def go(tx: Transaction) -> None:
            attempt = self._attempt(tx, attempt_id)
            if attempt["status"] != AttemptStatus.SENT.value:
                return
            tx.update(
                "attempts",
                attempt_id,
                {"status": AttemptStatus.UNKNOWN.value, "failure_reason": reason},
            )

        self._store.run_transaction(go)

    def release(self, attempt_id: str, reason: str) -> None:
        """The service refused the request before processing it; nothing was billed."""

        def go(tx: Transaction) -> None:
            attempt = self._attempt(tx, attempt_id)
            if attempt["status"] not in (AttemptStatus.RESERVED.value, AttemptStatus.SENT.value):
                return
            budgets = [tx.get("budgets", bid) for bid in attempt["budget_ids"]]
            for b in budgets:
                if b is None:
                    raise LedgerError("budget document missing")
                b["reserved_micros"] -= attempt["reserved_micros"]
                tx.set("budgets", b["budget_id"], b)
            tx.update(
                "attempts",
                attempt_id,
                {"status": AttemptStatus.FAILED.value, "failure_reason": reason},
            )

        self._store.run_transaction(go)

    def reconcile_sent(self, older_than_seconds: int = 120) -> list[str]:
        """Mark attempts stuck in ``sent`` (for example after a crash) as unknown.

        Their reservations stay held, because the calls may have been billed.
        """
        cutoff = self._clock().timestamp() - older_than_seconds
        stale = [
            a["attempt_id"]
            for a in self._store.list("attempts")
            if a["status"] == AttemptStatus.SENT.value
            and datetime.fromisoformat(a["created_at"]).timestamp() < cutoff
        ]
        for attempt_id in stale:
            self.mark_unknown(attempt_id, "process ended before a response was recorded")
        return stale

    def unknown_attempt(self, experiment_id: str, case_id: str) -> dict[str, Any] | None:
        """An earlier attempt for this case whose outcome is unknown, if any."""
        for a in self._store.list("attempts"):
            if (
                a["experiment_id"] == experiment_id
                and a["case_id"] == case_id
                and a["status"] == AttemptStatus.UNKNOWN.value
            ):
                return a
        return None

    # 7. Overrun

    def _overrun(self, attempt: dict[str, Any], actual_micros: int) -> None:
        app_id = attempt["app_id"]
        if self._store.get("apps", app_id) is not None:
            self._store.update("apps", app_id, {"paused": True})
        incident_id = f"overrun_{attempt['attempt_id']}"
        if self._store.get("incidents", incident_id) is None:
            self._store.create(
                "incidents",
                incident_id,
                {
                    "incident_id": incident_id,
                    "app_id": app_id,
                    "signal": "cost_overrun",
                    "threshold": attempt["reserved_micros"],
                    "observed": actual_micros,
                    "status": IncidentStatus.OPEN.value,
                    "actions": ["app paused by ledger"],
                    "opened_at": self._clock().isoformat(),
                    "closed_at": None,
                    "provenance": Provenance.MEASURED.value,
                },
            )

    @staticmethod
    def _attempt(tx: Transaction, attempt_id: str) -> dict[str, Any]:
        attempt = tx.get("attempts", attempt_id)
        if attempt is None:
            raise LedgerError(f"unknown attempt {attempt_id}")
        return attempt

    def summary(self) -> dict[str, Any]:
        """Settled spend by month and app, for artifacts/ledger_summary.json (MEASURED)."""
        months: dict[str, dict[str, Any]] = {}
        for a in self._store.list("attempts"):
            month = a["created_at"][:7]
            app = months.setdefault(month, {}).setdefault(
                a["app_id"], {"committed_micros": 0, "attempts": 0, "unknown": 0, "held_micros": 0}
            )
            app["attempts"] += 1
            if a["status"] == AttemptStatus.COMPLETED.value:
                app["committed_micros"] += a.get("actual_micros") or 0
            elif a["status"] == AttemptStatus.UNKNOWN.value:
                app["unknown"] += 1
                app["held_micros"] += a["reserved_micros"]
        return {
            "provenance": "MEASURED",
            "pricing": "list prices from the versioned price card",
            "exported_at": self._clock().isoformat(),
            "months": months,
        }

    def totals(self) -> dict[str, dict[str, Any]]:
        return {b["budget_id"]: b for b in self._store.list("budgets")}


# Bounded execution


@dataclass(frozen=True)
class CallOutcome:
    status: AttemptStatus  # COMPLETED, UNKNOWN, or FAILED (refused, nothing billed)
    attempt_id: str
    counted_input_tokens: int
    reservation_micros: int
    response: ProviderResponse | None = None
    actual_micros: int | None = None
    failure_reason: str | None = None


def call_with_budget(
    ledger: Ledger,
    provider: Provider,
    price: ModelPrice,
    limits: Limits,
    *,
    app_id: str,
    experiment_id: str,
    case_id: str,
    model_id: str,
    prompt: str,
    response_schema: dict[str, Any],
    cache: CacheHandle | None = None,
) -> CallOutcome:
    """One budgeted attempt. It never retries; the caller decides on a second attempt.

    With a cache, ``prompt`` is only the uncached suffix and the cached prefix is reserved
    at the cached-input rate.
    """
    counted = provider.count_tokens(model_id, prompt, response_schema).input_tokens
    cached = cache.token_count if cache else 0
    if counted + cached > limits.max_input_tokens:
        raise InputTooLargeError(
            f"{counted + cached} input tokens exceeds {limits.max_input_tokens}"
        )
    reservation = price.reservation_micros(counted, limits.max_output_tokens, cached)
    attempt_id = ledger.reserve(
        app_id=app_id,
        experiment_id=experiment_id,
        case_id=case_id,
        model_id=model_id,
        reservation_micros=reservation,
        max_attempts=limits.max_attempts_per_case,
    )
    ledger.mark_sent(attempt_id)
    try:
        response = provider.generate_structured(
            model_id,
            prompt,
            response_schema,
            limits.max_output_tokens,
            limits.deadline_seconds,
            cached_content=cache.name if cache else None,
        )
    except ProviderTimeoutError as exc:
        ledger.mark_unknown(attempt_id, str(exc))
        return CallOutcome(
            AttemptStatus.UNKNOWN, attempt_id, counted, reservation, failure_reason=str(exc)
        )
    except ProviderRejectedError as exc:
        ledger.release(attempt_id, str(exc))
        return CallOutcome(
            AttemptStatus.FAILED, attempt_id, counted, reservation, failure_reason=str(exc)
        )
    actual = price.cost_micros(
        response.input_tokens, response.output_tokens, response.cached_tokens
    )
    ledger.settle(
        attempt_id,
        actual_micros=actual,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cached_tokens=response.cached_tokens,
    )
    return CallOutcome(AttemptStatus.COMPLETED, attempt_id, counted, reservation, response, actual)


def charge_cache_storage(
    ledger: Ledger,
    price: ModelPrice,
    *,
    app_id: str,
    experiment_id: str,
    model_id: str,
    create: Callable[[], CacheHandle],
    expected_tokens: int,
    ttl_seconds: int,
) -> CacheHandle:
    """Reserve storage for the full TTL, create the cache, then settle the full TTL.

    Storage is charged for the whole TTL even if the cache is deleted early, so the
    recorded cost is an upper bound.
    """
    reservation = max(1, price.storage_micros(math.ceil(expected_tokens * 1.1), ttl_seconds))
    attempt_id = ledger.reserve(
        app_id=app_id,
        experiment_id=experiment_id,
        case_id=f"cache_storage:{uuid.uuid4().hex[:8]}",
        model_id=model_id,
        reservation_micros=reservation,
        max_attempts=1,
    )
    ledger.mark_sent(attempt_id)
    try:
        handle = create()
    except Exception as exc:
        ledger.release(attempt_id, f"cache create failed: {type(exc).__name__}")
        raise
    actual = max(1, price.storage_micros(handle.token_count, ttl_seconds))
    ledger.settle(
        attempt_id, actual_micros=actual, input_tokens=handle.token_count, output_tokens=0
    )
    return handle
