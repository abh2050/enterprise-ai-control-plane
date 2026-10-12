"""Governance Assist: deterministic attention scoring (console spec Section 9).

score = clamp(sum of signal points / 100, 0, 1). Every score stores its reason codes and
the input snapshot it used. Assist never changes an app record silently: dismiss,
mark safe, and schedule review are explicit user actions that write audit events.
"""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from control_plane.registry import ForbiddenError, Lifecycle, RegistryError, load_lifecycle
from control_plane.store import Store, Transaction

TERMINAL = {"retired"}
# Steady states are not queues, so time spent there is never a stall.
STALL_EXEMPT = {"monitored", "paused", "retired"}


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


def stage_durations(events: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Completed days spent in each stage, from stage_change events of all apps."""
    by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        if e["kind"] in ("stage_change", "created"):
            by_app[e["app_id"]].append(e)
    durations: dict[str, list[float]] = defaultdict(list)
    for app_events in by_app.values():
        app_events.sort(key=lambda e: e["created_at"])
        for prev, nxt in zip(app_events, app_events[1:], strict=False):
            stage = prev["to_stage"]
            days = (_parse(nxt["created_at"]) - _parse(prev["created_at"])).total_seconds()  # type: ignore[operator]
            durations[stage].append(days / 86400)
    return durations


def stage_medians(events: list[dict[str, Any]]) -> dict[str, float]:
    return {s: statistics.median(d) for s, d in stage_durations(events).items() if d}


def days_in_stage(app: dict[str, Any], now: datetime) -> float:
    entered = _parse(app["stage_entered_at"])
    return max(0.0, (now - entered).total_seconds() / 86400) if entered else 0.0


def is_stalled(
    app: dict[str, Any], medians: dict[str, float], lc: Lifecycle, now: datetime
) -> bool:
    if app["stage"] in STALL_EXEMPT or app["stage"] not in medians:
        return False
    multiple = float(lc.raw["stall"]["median_multiple"])
    return days_in_stage(app, now) > multiple * medians[app["stage"]]


def _suppressed(dismissals: list[dict[str, Any]], app_id: str, code: str, now: datetime) -> bool:
    for d in dismissals:
        if d["app_id"] == app_id and d["code"] in (code, "*"):
            until = _parse(d["until"])
            if until and until > now:
                return True
    return False


def score_app(
    app: dict[str, Any],
    *,
    medians: dict[str, float],
    open_incident_apps: set[str],
    dismissals: list[dict[str, Any]],
    owners_active: dict[str, bool],
    now: datetime,
    lc: Lifecycle | None = None,
) -> dict[str, Any]:
    lc = lc or load_lifecycle()
    cfg = lc.raw["assist"]
    sig = cfg["signals"]
    reasons: list[dict[str, Any]] = []

    def add(code: str, evidence: str) -> None:
        if code != "recent_evidence" and _suppressed(dismissals, app["app_id"], code, now):
            return
        reasons.append(
            {
                "code": code,
                "points": sig[code]["points"],
                "label": sig[code]["label"],
                "action": sig[code]["action"],
                "evidence": evidence,
            }
        )

    if app["stage"] not in TERMINAL:
        d = days_in_stage(app, now)
        median = medians.get(app["stage"])
        if is_stalled(app, medians, lc, now):
            add("stage_stall", f"{d:.0f} days in {app['stage']} vs median {median:.0f}")
        owner = app.get("owner")
        if not owner or not owners_active.get(owner, False):
            add("missing_owner", "owner field empty" if not owner else f"{owner} is inactive")
        if app["app_id"] in open_incident_apps:
            add("open_incident", "incidents with status open")
        budget = app.get("monthly_budget_micros") or 0
        spend = app.get("monthly_spend_micros") or 0
        if budget and spend > cfg["budget_pressure_ratio"] * budget:
            add("budget_pressure", f"spend {spend / 1e6:,.0f} of budget {budget / 1e6:,.0f} USD")
        expires = _parse(app.get("approvals_expire_at"))
        review = _parse(app.get("next_review_at"))
        if (
            expires
            and now <= expires <= now + timedelta(days=cfg["expiring_within_days"])
            and not (review and review <= expires)
        ):
            add("expiring_approval", f"approval expires {expires.date().isoformat()}")
        last_use = _parse(app.get("last_usage_at"))
        if app["stage"] in ("monitored", "controlled_activation") and (
            last_use is None or now - last_use > timedelta(days=cfg["dormant_days"])
        ):
            add(
                "dormant_app",
                "no usage recorded"
                if last_use is None
                else f"last usage {last_use.date().isoformat()}",
            )
        passed = _parse((app.get("evidence") or {}).get("last_passing_eval_at"))
        if passed and now - passed <= timedelta(days=cfg["recent_evidence_days"]):
            add("recent_evidence", f"passing evaluation {passed.date().isoformat()}")
    total = sum(r["points"] for r in reasons)
    score = min(1.0, max(0.0, total / 100))
    return {
        "app_id": app["app_id"],
        "score": round(score, 4),
        "flagged": score >= cfg["threshold"],
        "reasons": sorted(reasons, key=lambda r: -r["points"]),
        "snapshot": {
            "stage": app["stage"],
            "days_in_stage": round(days_in_stage(app, now), 1),
            "stage_median_days": medians.get(app["stage"]),
            "owner": app.get("owner"),
            "spend_micros": app.get("monthly_spend_micros"),
            "budget_micros": app.get("monthly_budget_micros"),
            "approvals_expire_at": app.get("approvals_expire_at"),
            "next_review_at": app.get("next_review_at"),
            "last_usage_at": app.get("last_usage_at"),
            "open_incident": app["app_id"] in open_incident_apps,
        },
        "scored_at": now.isoformat(),
    }


def all_events(store: Store, apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for a in apps for e in store.list(f"apps/{a['app_id']}/events")]


def score_all(store: Store, now: datetime | None = None) -> list[dict[str, Any]]:
    """Score every app and persist the scores. Runs nightly and after every mutation."""
    now = now or datetime.now(UTC)
    lc = load_lifecycle()
    apps = store.list("apps")
    medians = stage_medians(all_events(store, apps))
    open_apps = {i["app_id"] for i in store.list("incidents") if i.get("status") == "open"}
    users = {u["email"]: bool(u.get("active", True)) for u in store.list("users")}
    dismissals = store.list("assist_dismissals")
    scores = [
        score_app(
            a,
            medians=medians,
            open_incident_apps=open_apps,
            dismissals=dismissals,
            owners_active=users,
            now=now,
            lc=lc,
        )
        for a in apps
    ]
    for s in scores:
        store.set("assist_scores", s["app_id"], s)
    return scores


# Actions


def dismiss(
    store: Store, app_id: str, code: str, actor: str, reason: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    if not reason.strip():
        raise RegistryError("dismiss requires a reason")
    days = load_lifecycle().raw["assist"]["dismiss_suppress_days"]
    record = {
        "app_id": app_id,
        "code": code,
        "actor": actor,
        "reason": reason,
        "until": (now + timedelta(days=days)).isoformat(),
        "created_at": now.isoformat(),
    }

    def go(tx: Transaction) -> None:
        if tx.get("apps", app_id) is None:
            raise RegistryError(f"app {app_id} not found")
        tx.set("assist_dismissals", f"{app_id}__{code}", record)
        _audit(tx, app_id, "assist_dismiss", actor, f"dismissed {code}: {reason}", now)

    store.run_transaction(go)
    return record


def mark_safe(
    store: Store, app_id: str, actor: str, role: str, note: str, now: datetime | None = None
) -> dict[str, Any]:
    if role != "governance_admin":
        raise ForbiddenError("Only a governance admin can mark an app safe")
    now = now or datetime.now(UTC)
    if not note.strip():
        raise RegistryError("mark safe requires a note")
    days = load_lifecycle().raw["assist"]["dismiss_suppress_days"]
    record = {
        "app_id": app_id,
        "code": "*",
        "actor": actor,
        "reason": note,
        "until": (now + timedelta(days=days)).isoformat(),
        "created_at": now.isoformat(),
    }

    def go(tx: Transaction) -> None:
        if tx.get("apps", app_id) is None:
            raise RegistryError(f"app {app_id} not found")
        tx.set("assist_dismissals", f"{app_id}__*", record)
        _audit(tx, app_id, "assist_mark_safe", actor, note, now)

    store.run_transaction(go)
    return record


def schedule_review(
    store: Store,
    app_id: str,
    actor: str,
    review_at: datetime,
    expected_version: int,
    note: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Saves only when the user confirms (the API call is the confirmation)."""
    now = now or datetime.now(UTC)
    if review_at <= now:
        raise RegistryError("the review must be scheduled in the future")

    def go(tx: Transaction) -> dict[str, Any]:
        app = tx.get("apps", app_id)
        if app is None:
            raise RegistryError(f"app {app_id} not found")
        if app.get("version", 1) != expected_version:
            from control_plane.registry import VersionConflictError

            raise VersionConflictError(app)
        request_id = uuid.uuid4().hex
        tx.create(
            "review_requests",
            request_id,
            {
                "request_id": request_id,
                "app_id": app_id,
                "requested_by": actor,
                "review_at": review_at.isoformat(),
                "note": note,
                "status": "scheduled",
                "created_at": now.isoformat(),
            },
        )
        updates = {
            "next_review_at": review_at.isoformat(),
            "version": app.get("version", 1) + 1,
            "last_activity_at": now.isoformat(),
        }
        tx.update("apps", app_id, updates)
        _audit(
            tx,
            app_id,
            "review_scheduled",
            actor,
            f"review scheduled for {review_at.date().isoformat()}",
            now,
        )
        return {**app, **updates}

    return store.run_transaction(go)


def _audit(tx: Transaction, app_id: str, kind: str, actor: str, reason: str, now: datetime) -> None:
    event_id = uuid.uuid4().hex
    tx.create(
        f"apps/{app_id}/events",
        event_id,
        {
            "event_id": event_id,
            "app_id": app_id,
            "kind": kind,
            "from_stage": None,
            "to_stage": None,
            "actor": actor,
            "reason": reason,
            "evidence_refs": [],
            "created_at": now.isoformat(),
        },
    )
