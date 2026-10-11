"""Required tests 3, 4, 5 and the overrun rule for the budget ledger."""

import threading
from fractions import Fraction
from typing import Any

import pytest

from control_plane.budget import (
    AttemptsExhaustedError,
    BudgetExhaustedError,
    BudgetLimits,
    InputTooLargeError,
    Ledger,
    call_with_budget,
)
from control_plane.contracts import AttemptStatus, Limits, Provenance
from control_plane.pricing import ModelPrice
from control_plane.providers.base import (
    ProviderRejectedError,
    ProviderResponse,
    ProviderTimeoutError,
    TokenCount,
)
from control_plane.store import FileStore, Store

PRICE = ModelPrice(Fraction(1), Fraction(2), Fraction(1, 10))  # USD per 1M tokens
LIMITS = BudgetLimits(app_daily_micros=10_000, experiment_micros=10_000, total_micros=10_000)


def ledger(store: Store, limits: BudgetLimits = LIMITS) -> Ledger:
    return Ledger(store, limits)


def reserve(lg: Ledger, case: str, micros: int, max_attempts: int = 2) -> str:
    return lg.reserve(
        app_id="support-triage",
        experiment_id="exp1",
        case_id=case,
        model_id="m",
        reservation_micros=micros,
        max_attempts=max_attempts,
    )


def test_reservation_math_matches_section_7() -> None:
    # 1,000 counted tokens -> 1,100 padded at $1/M = 1,100 micros; 256 cap at $2/M = 512
    assert PRICE.reservation_micros(1000, 256) == 1612
    assert PRICE.reservation_micros(999, 0) == 1099  # ceil(1098.9)
    # actual: 900 uncached at $1 + 100 cached at $0.10 + 40 output at $2
    assert PRICE.cost_micros(1000, 40, cached_tokens=100) == 900 + 10 + 80


def test_concurrent_reservations_never_over_admit(any_store: Store) -> None:
    """Test 3: 20 concurrent reservations near the cap never over admit."""
    lg = ledger(any_store)
    admitted: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        try:
            aid = reserve(lg, f"case{i}", 700)  # 14 fit under 10,000; 6 must be refused
            with lock:
                admitted.append(aid)
        except BudgetExhaustedError:
            pass
        except Exception as exc:  # Firestore contention aborts count as refusals
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    totals = lg.totals()
    for b in totals.values():
        assert b["reserved_micros"] + b["committed_micros"] <= b["limit_usd_micros"]
        assert b["reserved_micros"] == 700 * len(admitted)
    assert len(admitted) <= 14
    assert len(any_store.list("attempts")) == len(admitted)


def test_repeated_settlement_changes_nothing(any_store: Store) -> None:
    """Test 4."""
    lg = ledger(any_store)
    aid = reserve(lg, "c1", 1000)
    lg.mark_sent(aid)
    assert lg.settle(aid, actual_micros=400, input_tokens=300, output_tokens=50) is True
    before = lg.totals()
    assert lg.settle(aid, actual_micros=400, input_tokens=300, output_tokens=50) is False
    assert lg.settle(aid, actual_micros=999, input_tokens=1, output_tokens=1) is False
    assert lg.totals() == before
    total = before["allowance_total"]
    assert total["reserved_micros"] == 0 and total["committed_micros"] == 400


class FakeProvider:
    provenance = Provenance.FIXTURE
    backend = "fake"

    def __init__(self, behaviour: str, tokens: int = 1000) -> None:
        self.behaviour = behaviour
        self.tokens = tokens
        self.calls = 0

    def count_tokens(self, model_id: str, prompt: str, response_schema: Any = None) -> TokenCount:
        return TokenCount(self.tokens)

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
        cached_content: str | None = None,
    ) -> ProviderResponse:
        self.calls += 1
        if self.behaviour == "timeout":
            raise ProviderTimeoutError("deadline passed after send")
        if self.behaviour == "429":
            raise ProviderRejectedError(429, "RESOURCE_EXHAUSTED")
        out = 5000 if self.behaviour == "overrun" else 40
        return ProviderResponse({"intent": "x"}, self.tokens, out, 10, model_id, Provenance.FIXTURE)


def run(lg: Ledger, provider: FakeProvider, case: str = "c1", limits: Limits | None = None):  # type: ignore[no-untyped-def]
    return call_with_budget(
        lg,
        provider,
        PRICE,
        limits or Limits(max_output_tokens=256),
        app_id="support-triage",
        experiment_id="exp1",
        case_id=case,
        model_id="m",
        prompt="p",
        response_schema={},
    )


def test_timeout_after_send_keeps_reservation_and_does_not_retry(any_store: Store) -> None:
    """Test 5."""
    lg = ledger(any_store)
    provider = FakeProvider("timeout")
    outcome = run(lg, provider)
    assert outcome.status is AttemptStatus.UNKNOWN
    assert provider.calls == 1
    attempt = any_store.get("attempts", outcome.attempt_id)
    assert attempt is not None and attempt["status"] == "unknown"
    assert lg.totals()["allowance_total"]["reserved_micros"] == outcome.reservation_micros


def test_refusal_before_processing_releases_reservation(any_store: Store) -> None:
    lg = ledger(any_store)
    outcome = run(lg, FakeProvider("429"))
    assert outcome.status is AttemptStatus.FAILED
    assert lg.totals()["allowance_total"]["reserved_micros"] == 0


def test_at_most_two_attempts_per_case(any_store: Store) -> None:
    lg = ledger(any_store)
    run(lg, FakeProvider("429"))
    run(lg, FakeProvider("429"))
    with pytest.raises(AttemptsExhaustedError):
        run(lg, FakeProvider("ok"))


def test_input_cap_blocks_before_reserving(any_store: Store) -> None:
    lg = ledger(any_store)
    with pytest.raises(InputTooLargeError):
        run(lg, FakeProvider("ok", tokens=8001))
    assert any_store.list("attempts") == []


def test_exhausted_budget_blocks_and_records_event(any_store: Store) -> None:
    lg = ledger(any_store, BudgetLimits(10_000, 10_000, 1_000))
    with pytest.raises(BudgetExhaustedError):
        run(lg, FakeProvider("ok"))
    events = any_store.list("budget_events")
    assert [e["kind"] for e in events] == ["budget_exhausted"]


def test_overrun_pauses_app_and_opens_incident(any_store: Store) -> None:
    any_store.create("apps", "support-triage", {"app_id": "support-triage", "paused": False})
    lg = ledger(any_store, BudgetLimits(100_000, 100_000, 100_000))
    outcome = run(lg, FakeProvider("overrun"))
    assert outcome.actual_micros is not None and outcome.actual_micros > outcome.reservation_micros
    assert any_store.get("apps", "support-triage")["paused"] is True  # type: ignore[index]
    incidents = any_store.list("incidents")
    assert len(incidents) == 1 and incidents[0]["signal"] == "cost_overrun"


def test_file_store_ledger_survives_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    lg = ledger(FileStore(tmp_path))
    run(lg, FakeProvider("ok"))
    reopened = ledger(FileStore(tmp_path))
    assert reopened.totals()["allowance_total"]["committed_micros"] > 0


def test_configured_limit_applies_to_existing_budget(any_store: Store) -> None:
    tight = ledger(any_store, BudgetLimits(1_000, 100_000, 100_000))
    reserve(tight, "c1", 900)
    with pytest.raises(BudgetExhaustedError):
        reserve(tight, "c2", 200)
    raised = ledger(any_store, BudgetLimits(2_000, 100_000, 100_000))
    reserve(raised, "c2", 200)  # the raised daily limit applies to today's document


def test_reconcile_marks_stuck_sent_attempt_unknown(any_store: Store) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    old = Ledger(any_store, LIMITS, clock=lambda: now - timedelta(minutes=10))
    aid = reserve(old, "c1", 500)
    old.mark_sent(aid)  # the process crashed before a response was recorded
    lg = ledger(any_store)
    assert lg.reconcile_sent() == [aid]
    assert any_store.get("attempts", aid)["status"] == "unknown"  # type: ignore[index]
    assert lg.totals()["allowance_total"]["reserved_micros"] == 500  # still held
    assert lg.unknown_attempt("exp1", "c1") is not None
    assert lg.unknown_attempt("exp1", "c2") is None
