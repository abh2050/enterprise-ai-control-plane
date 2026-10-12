from datetime import UTC, datetime, timedelta

import pytest

from control_plane.assist import dismiss, mark_safe, schedule_review, score_all, score_app
from control_plane.registry import ForbiddenError
from control_plane.store import MemoryStore

NOW = datetime(2026, 10, 12, tzinfo=UTC)


def app(**kw):  # type: ignore[no-untyped-def]
    base = {
        "app_id": "a1",
        "stage": "review_gates",
        "owner": "o@x.com",
        "stage_entered_at": (NOW - timedelta(days=5)).isoformat(),
        "monthly_budget_micros": 100,
        "monthly_spend_micros": 10,
        "last_usage_at": NOW.isoformat(),
        "evidence": {},
        "version": 1,
    }
    return {**base, **kw}


def score(a, **kw):  # type: ignore[no-untyped-def]
    args = {
        "medians": {"review_gates": 10.0},
        "open_incident_apps": set(),
        "dismissals": [],
        "owners_active": {"o@x.com": True},
        "now": NOW,
    }
    return score_app(a, **{**args, **kw})


def test_healthy_app_scores_zero() -> None:
    s = score(app())
    assert s["score"] == 0 and not s["flagged"] and s["reasons"] == []


def test_points_add_and_clamp() -> None:
    s = score(
        app(
            owner=None,
            monthly_spend_micros=95,
            stage_entered_at=(NOW - timedelta(days=20)).isoformat(),
        ),
        open_incident_apps={"a1"},
    )
    # stall 30 + missing owner 35 + incident 35 + budget 20 = 120 -> clamped to 1
    assert s["score"] == 1.0 and s["flagged"]
    assert {r["code"] for r in s["reasons"]} == {
        "stage_stall",
        "missing_owner",
        "open_incident",
        "budget_pressure",
    }
    assert s["snapshot"]["open_incident"] is True


def test_threshold_and_recent_evidence_credit() -> None:
    a = app(owner=None, stage_entered_at=(NOW - timedelta(days=20)).isoformat())
    assert score(a)["score"] == pytest.approx(0.65) and score(a)["flagged"]
    a["evidence"] = {"last_passing_eval_at": (NOW - timedelta(days=2)).isoformat()}
    assert score(a)["score"] == pytest.approx(0.50) and not score(a)["flagged"]


def test_expiring_approval_cleared_by_scheduled_review() -> None:
    a = app(approvals_expire_at=(NOW + timedelta(days=5)).isoformat())
    assert [r["code"] for r in score(a)["reasons"]] == ["expiring_approval"]
    a["next_review_at"] = (NOW + timedelta(days=3)).isoformat()
    assert score(a)["reasons"] == []


def test_dormant_only_for_live_stages() -> None:
    assert score(app(stage="monitored", last_usage_at=None))["reasons"][0]["code"] == "dormant_app"
    assert score(app(stage="intake", last_usage_at=None))["reasons"] == []


def test_production_time_is_never_a_stall() -> None:
    long_ago = (NOW - timedelta(days=200)).isoformat()
    assert (
        score(app(stage="monitored", stage_entered_at=long_ago), medians={"monitored": 10.0})[
            "reasons"
        ]
        == []
    )


def test_actions_audit_and_suppress() -> None:
    store = MemoryStore()
    store.create("apps", "a1", app(owner=None))
    store.create("users", "o@x.com", {"email": "o@x.com", "active": True})
    assert score_all(store, NOW)[0]["reasons"][0]["code"] == "missing_owner"
    dismiss(store, "a1", "missing_owner", "admin@x.com", "owner change in progress", NOW)
    assert score_all(store, NOW)[0]["reasons"] == []
    assert score_all(store, NOW + timedelta(days=8))[0]["reasons"]  # suppression expires
    with pytest.raises(ForbiddenError):
        mark_safe(store, "a1", "r@x.com", "reviewer", "fine", NOW)
    mark_safe(store, "a1", "admin@x.com", "governance_admin", "accepted risk", NOW)
    kinds = [e["kind"] for e in store.list("apps/a1/events")]
    assert kinds == ["assist_dismiss", "assist_mark_safe"]
    updated = schedule_review(store, "a1", "admin@x.com", NOW + timedelta(days=3), 1, now=NOW)
    assert updated["next_review_at"] and updated["version"] == 2
    assert len(store.list("review_requests")) == 1
