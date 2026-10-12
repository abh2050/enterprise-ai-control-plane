"""Required test 1 and the Pipeline move rules from configs/lifecycle.yaml."""

from datetime import UTC, datetime
from typing import Any

import pytest

from control_plane.contracts import Role
from control_plane.registry import (
    Actor,
    ForbiddenError,
    RequirementMissingError,
    VersionConflictError,
    approve_gate,
    check_move,
    move,
)
from control_plane.store import Store

NOW = datetime(2026, 10, 12, tzinfo=UTC)
OWNER = Actor("owner@example.com", Role.APP_OWNER)
OTHER_OWNER = Actor("owner2@example.com", Role.APP_OWNER)
REVIEWER = Actor("reviewer@example.com", Role.REVIEWER)
SECURITY = Actor("security@example.com", Role.REVIEWER, security_reviewer=True)
ADMIN = Actor("admin@example.com", Role.GOVERNANCE_ADMIN)
VIEWER = Actor("exec@example.com", Role.EXECUTIVE_VIEWER)

CASE = {
    "monthly_volume": {
        "value": 1000,
        "unit": "cases",
        "provenance": "ASSUMPTION",
        "justification": "x",
    },
    "value_hypothesis": "Saves triage time",
    "monthly_value_usd": {
        "value": 5000,
        "unit": "USD",
        "provenance": "ASSUMPTION",
        "justification": "x",
    },
    "monthly_cost_estimate_usd": {
        "value": 300,
        "unit": "USD",
        "provenance": "ASSUMPTION",
        "justification": "x",
    },
}


def make_app(
    store: Store, stage: str = "intake", platform: str = "copilot", risk: str = "low", **extra: Any
) -> dict[str, Any]:
    app = {
        "app_id": "a1",
        "name": "App",
        "owner": OWNER.email,
        "business_unit": "Ops",
        "platform": platform,
        "business_problem": "word " * 30,
        "risk_tier": risk,
        "stage": stage,
        "version": 1,
        "monthly_budget_micros": 1,
        "gates": {},
        "evidence": {},
        "stage_entered_at": NOW.isoformat(),
        "created_at": NOW.isoformat(),
        "provenance": "FIXTURE",
        **extra,
    }
    store.create("apps", "a1", app)
    return app


def events(store: Store) -> list[dict[str, Any]]:
    return store.list("apps/a1/events")


def test_illegal_transition_rejected(any_store: Store) -> None:
    make_app(any_store, business_case=CASE)
    with pytest.raises(RequirementMissingError) as err:
        move(any_store, "a1", "monitored", OWNER, 1, now=NOW)
    assert err.value.code == "not_allowed"
    assert any_store.get("apps", "a1")["stage"] == "intake"  # type: ignore[index]
    assert events(any_store) == []


def test_missing_requirement_reported_before_mutation(any_store: Store) -> None:
    make_app(any_store)  # no business case
    with pytest.raises(RequirementMissingError) as err:
        move(any_store, "a1", "business_case", OWNER, 1, now=NOW)
    assert err.value.code == "business_case_fields"
    assert "value hypothesis" in str(err.value)
    assert any_store.get("apps", "a1")["version"] == 1  # type: ignore[index]


def test_owner_moves_and_event_written(any_store: Store) -> None:
    make_app(any_store, business_case=CASE)
    app, event = move(any_store, "a1", "business_case", OWNER, 1, now=NOW)
    assert app["stage"] == "business_case" and app["version"] == 2
    assert [e["to_stage"] for e in events(any_store)] == ["business_case"]
    assert event["actor"] == OWNER.email


def test_stale_version_conflicts(any_store: Store) -> None:
    make_app(any_store, business_case=CASE)
    move(any_store, "a1", "business_case", OWNER, 1, now=NOW)
    with pytest.raises(VersionConflictError) as err:
        move(any_store, "a1", "review_gates", OWNER, 1, now=NOW)  # second user, stale version
    assert err.value.current["version"] == 2


def test_roles_and_ownership(any_store: Store) -> None:
    make_app(any_store, business_case=CASE)
    with pytest.raises(ForbiddenError):
        move(any_store, "a1", "business_case", VIEWER, 1, now=NOW)
    with pytest.raises(ForbiddenError):
        move(any_store, "a1", "business_case", OTHER_OWNER, 1, now=NOW)


def test_submitter_cannot_approve_own_gate(any_store: Store) -> None:
    make_app(any_store, stage="business_case", business_case=CASE)
    move(any_store, "a1", "review_gates", ADMIN, 1, now=NOW)  # admin submits
    with pytest.raises(ForbiddenError, match="different person"):
        approve_gate(any_store, "a1", "reviewer", ADMIN, "approve", "looks fine", now=NOW)
    out = approve_gate(any_store, "a1", "reviewer", REVIEWER, "approve", "evidence ok", now=NOW)
    assert "reviewer" in out["gates"]
    assert any_store.list("reviews")[0]["reviewer"] == REVIEWER.email


def test_high_risk_needs_governance_and_security(any_store: Store) -> None:
    make_app(
        any_store, stage="review_gates", risk="high", business_case=CASE, submitted_by=OWNER.email
    )
    with pytest.raises(ForbiddenError):
        approve_gate(any_store, "a1", "security", REVIEWER, "approve", "ok", now=NOW)
    approve_gate(any_store, "a1", "governance", ADMIN, "approve", "ok", now=NOW)
    app = any_store.get("apps", "a1")
    assert app is not None
    check = check_move(app, "monitored", ADMIN, reason="publish", now=NOW)
    assert check.code == "gates_approved"
    approve_gate(any_store, "a1", "security", SECURITY, "approve", "ok", now=NOW)
    app = any_store.get("apps", "a1")
    assert app is not None
    move(any_store, "a1", "monitored", ADMIN, app["version"], reason="published", now=NOW)


def test_external_apps_cannot_enter_managed_stages(any_store: Store) -> None:
    make_app(any_store, stage="review_gates")
    app = any_store.get("apps", "a1")
    assert app is not None
    assert check_move(app, "evaluation", OWNER, now=NOW).code == "managed_only"


def test_pause_needs_reason_and_returns_only_to_prior(any_store: Store) -> None:
    make_app(any_store, stage="monitored")
    with pytest.raises(RequirementMissingError):
        move(any_store, "a1", "paused", ADMIN, 1, now=NOW)
    app, _ = move(any_store, "a1", "paused", ADMIN, 1, reason="incident", now=NOW)
    assert app["prior_stage"] == "monitored"
    assert check_move(app, "intake", ADMIN, now=NOW).code == "paused_prior_only"
    app, _ = move(any_store, "a1", "monitored", ADMIN, app["version"], now=NOW)
    assert app["stage"] == "monitored" and app["paused"] is False


def test_retire_needs_reason_and_is_final(any_store: Store) -> None:
    make_app(any_store, stage="business_case")
    with pytest.raises(RequirementMissingError):
        move(any_store, "a1", "retired", ADMIN, 1, now=NOW)
    app, _ = move(any_store, "a1", "retired", ADMIN, 1, reason="duplicate", now=NOW)
    assert check_move(app, "intake", ADMIN, now=NOW).code == "retired"


def test_shadow_requires_passing_scorecard(any_store: Store) -> None:
    make_app(any_store, stage="evaluation", platform="managed", active_config_id="c1")
    app = any_store.get("apps", "a1")
    assert app is not None
    assert check_move(app, "shadow", OWNER, now=NOW).code == "scorecard_passed"
