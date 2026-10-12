"""Application lifecycle state machine (Section 5 and console spec Section 9).

Every move:
- runs in one store transaction,
- checks the caller's expected version and raises ``VersionConflictError`` with the
  current record when it is stale (the API returns 409),
- checks the caller's role and the destination's requirements from
  configs/lifecycle.yaml, reporting the first missing requirement before any mutation,
- writes an append-only event with actor, reason, and evidence references.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from control_plane.contracts import Platform, Role, Stage
from control_plane.store import Store, Transaction

LIFECYCLE_PATH = Path(__file__).resolve().parents[2] / "configs" / "lifecycle.yaml"
EXTERNAL_PLATFORMS = {Platform.ABACUS.value, Platform.COPILOT.value, Platform.CUSTOM.value}


class RegistryError(Exception):
    status = 400


class NotFoundError(RegistryError):
    status = 404


class ForbiddenError(RegistryError):
    status = 403


class RequirementMissingError(RegistryError):
    status = 422

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class VersionConflictError(RegistryError):
    status = 409

    def __init__(self, current: dict[str, Any]) -> None:
        super().__init__("the app changed since you loaded it")
        self.current = current


@dataclass(frozen=True)
class Actor:
    email: str
    role: Role
    security_reviewer: bool = False


@dataclass(frozen=True)
class Lifecycle:
    raw: dict[str, Any]
    stages: list[str] = field(default_factory=list)

    @property
    def transitions(self) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = self.raw["transitions"]
        return rules

    def message(self, code: str) -> str:
        messages: dict[str, str] = self.raw["requirement_messages"]
        return messages[code]

    def required_gates(self, risk_tier: str) -> list[str]:
        gates: list[str] = self.raw["review_gates"][risk_tier]
        return gates


@lru_cache
def load_lifecycle(path: Path = LIFECYCLE_PATH) -> Lifecycle:
    raw = yaml.safe_load(path.read_text())
    return Lifecycle(raw=raw, stages=list(raw["stages"]))


def _now() -> datetime:
    return datetime.now(UTC)


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


# Requirement checks


def _has_business_case(app: dict[str, Any]) -> bool:
    case = app.get("business_case")
    return bool(
        case
        and case.get("monthly_volume")
        and case.get("value_hypothesis")
        and case.get("monthly_cost_estimate_usd")
    )


def gates_approved(app: dict[str, Any], lifecycle: Lifecycle, now: datetime) -> bool:
    gates = app.get("gates") or {}
    for gate in lifecycle.required_gates(app["risk_tier"]):
        approval = gates.get(gate)
        expires = _parse(approval.get("expires_at")) if approval else None
        if not approval or (expires is not None and expires < now):
            return False
    return True


def _requirement_met(
    code: str, app: dict[str, Any], lifecycle: Lifecycle, reason: str | None, now: datetime
) -> bool:
    evidence = app.get("evidence") or {}
    checks: dict[str, Callable[[], bool]] = {
        "business_case_fields": lambda: _has_business_case(app),
        "gates_approved": lambda: gates_approved(app, lifecycle, now),
        "managed_config": lambda: (
            app["platform"] == Platform.MANAGED.value and bool(app.get("active_config_id"))
        ),
        "external_app": lambda: app["platform"] in EXTERNAL_PLATFORMS,
        "scorecard_passed": lambda: bool(evidence.get("scorecard_passed")),
        "release_decision": lambda: (
            evidence.get("release_decision") in ("activate_cohort", "activate_full")
        ),
        "activation": lambda: (
            evidence.get("release_decision") in ("activate_cohort", "activate_full")
        ),
        "reason": lambda: bool(reason and reason.strip()),
    }
    if code not in checks:
        raise RegistryError(f"unknown requirement {code}")
    return checks[code]()


@dataclass(frozen=True)
class MoveCheck:
    allowed: bool
    code: str | None = None
    message: str | None = None
    transition: dict[str, Any] | None = None


def check_move(
    app: dict[str, Any],
    to_stage: str,
    actor: Actor,
    reason: str | None = None,
    now: datetime | None = None,
    lifecycle: Lifecycle | None = None,
) -> MoveCheck:
    """Validate a move without changing anything. Order: shape, role, requirements."""
    lc = lifecycle or load_lifecycle()
    now = now or _now()
    current = app["stage"]
    if to_stage not in lc.stages:
        return MoveCheck(False, "unknown_stage", f"{to_stage} is not a lifecycle stage")
    if current == Stage.RETIRED.value:
        return MoveCheck(False, "retired", "Retired apps cannot move")
    if to_stage == current:
        return MoveCheck(False, "same_stage", "The app is already in this stage")
    if to_stage in lc.raw["managed_only"] and app["platform"] != Platform.MANAGED.value:
        return MoveCheck(False, "managed_only", f"Only managed apps enter {to_stage}")

    candidates = []
    for t in lc.transitions:
        if t["from"] not in (current, "any"):
            continue
        target = app.get("prior_stage") if t["to"] == "prior_stage" else t["to"]
        if target == to_stage and not (
            t["from"] == "any" and current == Stage.PAUSED.value and to_stage != Stage.RETIRED.value
        ):
            candidates.append(t)
    if not candidates:
        if current == Stage.PAUSED.value:
            return MoveCheck(
                False,
                "paused_prior_only",
                f"Paused apps can only return to their prior stage ({app.get('prior_stage')})",
            )
        return MoveCheck(False, "not_allowed", f"No move from {current} to {to_stage}")
    transition = candidates[0]
    if actor.role.value not in transition["roles"]:
        return MoveCheck(
            False, "role", f"Your role ({actor.role.value}) cannot make this move", transition
        )
    if actor.role is Role.APP_OWNER and app.get("owner") != actor.email:
        return MoveCheck(False, "not_owner", "Only the app's owner can make this move", transition)
    for code in transition["requires"]:
        if not _requirement_met(code, app, lc, reason, now):
            return MoveCheck(False, code, lc.message(code), transition)
    return MoveCheck(True, transition=transition)


# Mutations


def _event(
    tx: Transaction,
    app_id: str,
    kind: str,
    from_stage: str | None,
    to_stage: str | None,
    actor: str,
    reason: str,
    evidence_refs: list[str],
    now: datetime,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_id = uuid.uuid4().hex
    event: dict[str, Any] = {
        "event_id": event_id,
        "app_id": app_id,
        "kind": kind,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "actor": actor,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "created_at": now.isoformat(),
    }
    if extra:
        event.update(extra)
    tx.create(f"apps/{app_id}/events", event_id, event)
    return event


def move(
    store: Store,
    app_id: str,
    to_stage: str,
    actor: Actor,
    expected_version: int,
    reason: str | None = None,
    evidence_refs: list[str] | None = None,
    source: str = "api",
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Move an app. Returns (updated app, event)."""
    now = now or _now()

    def go(tx: Transaction) -> tuple[dict[str, Any], dict[str, Any]]:
        app = tx.get("apps", app_id)
        if app is None:
            raise NotFoundError(f"app {app_id} not found")
        check = check_move(app, to_stage, actor, reason, now)
        if not check.allowed and check.code in ("role", "not_owner"):
            raise ForbiddenError(check.message or "forbidden")
        if app.get("version", 1) != expected_version:
            raise VersionConflictError(app)
        if not check.allowed:
            raise RequirementMissingError(check.code or "invalid", check.message or "invalid")
        from_stage = app["stage"]
        updates: dict[str, Any] = {
            "stage": to_stage,
            "stage_entered_at": now.isoformat(),
            "version": app.get("version", 1) + 1,
            "last_activity_at": now.isoformat(),
            "paused": to_stage == Stage.PAUSED.value,
        }
        if to_stage == Stage.PAUSED.value:
            updates["prior_stage"] = from_stage
        elif from_stage == Stage.PAUSED.value:
            updates["prior_stage"] = None
        if to_stage == Stage.REVIEW_GATES.value:
            updates["submitted_by"] = actor.email
        tx.update("apps", app_id, updates)
        event = _event(
            tx,
            app_id,
            "stage_change",
            from_stage,
            to_stage,
            actor.email,
            reason or f"moved via {source}",
            evidence_refs or [],
            now,
            extra={
                "source": source,
                "previous": {
                    k: app.get(k)
                    for k in ("stage", "stage_entered_at", "prior_stage", "paused", "submitted_by")
                },
            },
        )
        return {**app, **updates}, event

    return store.run_transaction(go)


UNDO_WINDOW = timedelta(seconds=15)  # 10 s in the UI plus network grace


def undo_move(
    store: Store,
    app_id: str,
    event_id: str,
    actor: Actor,
    expected_version: int,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reverse the caller's own latest move within the undo window. Writes a new event;
    the original event stays in the append-only history."""
    now = now or _now()

    def go(tx: Transaction) -> tuple[dict[str, Any], dict[str, Any]]:
        app = tx.get("apps", app_id)
        if app is None:
            raise NotFoundError(f"app {app_id} not found")
        original = tx.get(f"apps/{app_id}/events", event_id)
        if original is None or original.get("kind") != "stage_change":
            raise NotFoundError("move not found")
        if original["actor"] != actor.email:
            raise ForbiddenError("Only the person who made a move can undo it")
        if now - datetime.fromisoformat(original["created_at"]) > UNDO_WINDOW:
            raise RegistryError("The undo window has passed")
        if app.get("version", 1) != expected_version or app["stage"] != original["to_stage"]:
            raise VersionConflictError(app)
        prev = original.get("previous") or {}
        updates = {
            "stage": prev.get("stage", original["from_stage"]),
            "stage_entered_at": prev.get("stage_entered_at", now.isoformat()),
            "prior_stage": prev.get("prior_stage"),
            "paused": bool(prev.get("paused")),
            "submitted_by": prev.get("submitted_by"),
            "version": app.get("version", 1) + 1,
            "last_activity_at": now.isoformat(),
        }
        tx.update("apps", app_id, updates)
        event = _event(
            tx,
            app_id,
            "stage_change_undone",
            original["to_stage"],
            updates["stage"],
            actor.email,
            f"Undid move {event_id}",
            [f"apps/{app_id}/events/{event_id}"],
            now,
        )
        return {**app, **updates}, event

    return store.run_transaction(go)


def approve_gate(
    store: Store,
    app_id: str,
    gate: str,
    actor: Actor,
    decision: str,
    reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record a reviewer's decision on one review gate. The submitter can never approve."""
    now = now or _now()
    lc = load_lifecycle()
    if decision not in ("approve", "reject"):
        raise RegistryError("decision must be approve or reject")
    if not reason.strip():
        raise RequirementMissingError("reason", lc.message("reason"))

    def go(tx: Transaction) -> dict[str, Any]:
        app = tx.get("apps", app_id)
        if app is None:
            raise NotFoundError(f"app {app_id} not found")
        if app["stage"] != Stage.REVIEW_GATES.value:
            raise RegistryError("the app is not waiting at review gates")
        if gate not in lc.required_gates(app["risk_tier"]):
            raise RegistryError(f"{gate} is not required for {app['risk_tier']} risk")
        if actor.email in (app.get("submitted_by"), app.get("owner")):
            raise ForbiddenError("A different person must approve: you submitted this app")
        allowed_roles = lc.raw["gate_approvers"][gate]
        permitted = actor.role.value in allowed_roles or (
            "security_reviewer" in allowed_roles and actor.security_reviewer
        )
        if not permitted:
            raise ForbiddenError(f"Your role cannot decide the {gate} gate")
        review_id = uuid.uuid4().hex
        tx.create(
            "reviews",
            review_id,
            {
                "review_id": review_id,
                "subject": "gate",
                "subject_id": f"{app_id}:{gate}",
                "reviewer": actor.email,
                "decision": decision,
                "reason": reason,
                "created_at": now.isoformat(),
            },
        )
        gates = dict(app.get("gates") or {})
        if decision == "approve":
            gates[gate] = {
                "gate": gate,
                "approved_by": actor.email,
                "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(days=lc.raw["approval_valid_days"])).isoformat(),
                "review_id": review_id,
            }
        else:
            gates.pop(gate, None)
        expiries = [g["expires_at"] for g in gates.values()]
        tx.update(
            "apps",
            app_id,
            {
                "gates": gates,
                "approvals_expire_at": min(expiries) if expiries else None,
                "version": app.get("version", 1) + 1,
                "last_activity_at": now.isoformat(),
                "last_decision": f"{gate} {decision}d",
            },
        )
        _event(
            tx,
            app_id,
            f"gate_{decision}",
            app["stage"],
            app["stage"],
            actor.email,
            reason,
            [f"reviews/{review_id}"],
            now,
        )
        return {"review_id": review_id, "gates": gates}

    return store.run_transaction(go)


def pending_gate_items(app: dict[str, Any], lifecycle: Lifecycle | None = None) -> list[str]:
    lc = lifecycle or load_lifecycle()
    if app["stage"] != Stage.REVIEW_GATES.value:
        return []
    approved = app.get("gates") or {}
    return [g for g in lc.required_gates(app["risk_tier"]) if g not in approved]


def word_count(text: str) -> int:
    return len(text.split())
