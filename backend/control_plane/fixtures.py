"""Local identities, the SYNTHETIC registry seed, and measured ledger spend.

- Fixture users cover all four roles for local sign-in.
- data/registry_seed.json holds 40 SYNTHETIC apps with 120 days of history.
- artifacts/ledger_summary.json holds MEASURED model spend exported from the ledger.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from control_plane.contracts import Role, User
from control_plane.store import Store

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "registry_seed.json"
LEDGER_SUMMARY = ROOT / "artifacts" / "ledger_summary.json"

FIXTURE_USERS: list[tuple[str, Role, bool]] = [
    ("owner@example.com", Role.APP_OWNER, False),
    ("owner2@example.com", Role.APP_OWNER, False),
    ("reviewer@example.com", Role.REVIEWER, False),
    ("security@example.com", Role.REVIEWER, True),
    ("admin@example.com", Role.GOVERNANCE_ADMIN, False),
    ("exec@example.com", Role.EXECUTIVE_VIEWER, False),
]


def fixture_users(now: datetime) -> list[User]:
    return [
        User(email=email, role=role, security_reviewer=sec, created_at=now)
        for email, role, sec in FIXTURE_USERS
    ]


def load_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def ledger_summary() -> dict[str, Any]:
    if not LEDGER_SUMMARY.exists():
        return {"months": {}}
    data: dict[str, Any] = json.loads(LEDGER_SUMMARY.read_text())
    return data


def _shift(node: Any, delta: timedelta) -> Any:
    """Shift every ISO timestamp under keys ending in ``_at`` by ``delta``."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key.endswith("_at") and isinstance(value, str):
                out[key] = (datetime.fromisoformat(value) + delta).isoformat()
            else:
                out[key] = _shift(value, delta)
        return out
    if isinstance(node, list):
        return [_shift(v, delta) for v in node]
    return node


def seed_registry(store: Store, now: datetime | None = None) -> dict[str, int]:
    """Load users, SYNTHETIC apps, events, and incidents. Overwrites mutable records.

    Seed history ends on its reference date. Timestamps are shifted so the history ends
    at ``now``, which keeps days in stage, stalls, and expiring approvals stable no
    matter when the console is opened.
    """
    now = now or datetime.now(UTC)
    raw = load_seed()
    seed = _shift(raw, now - datetime.fromisoformat(raw["reference_date"]))
    for user in fixture_users(now):
        store.set("users", user.email, user.model_dump(mode="json"))
    for user in seed["users"]:
        store.set("users", user["email"], user)
    for app in seed["apps"]:
        store.set("apps", app["app_id"], app)
    loaded_events = 0
    for event in seed["events"]:
        collection = f"apps/{event['app_id']}/events"
        if store.get(collection, event["event_id"]) is None:
            store.create(collection, event["event_id"], event)
            loaded_events += 1
    for incident in seed["incidents"]:
        store.set("incidents", incident["incident_id"], incident)
    load_m5_evidence(store)
    from control_plane.assist import score_all

    score_all(store, now)
    return {
        "users": len(FIXTURE_USERS) + len(seed["users"]),
        "apps": len(seed["apps"]),
        "events": loaded_events,
        "incidents": len(seed["incidents"]),
    }


# Kept for callers that only need identities.
def seed_fixture(store: Store, now: datetime | None = None) -> dict[str, int]:
    return seed_registry(store, now)


def load_m5_evidence(store: Store) -> dict[str, int]:
    """Releases, drill incidents, their audit events, and routed cases for review.

    Everything comes from committed artifacts. Case text is read from the local Banking77
    files (data/raw, gitignored) and is shown only in the console.
    """
    from control_plane.monitoring import INCIDENT_DIR, MONITORING_DIR, SHADOW_DIR
    from control_plane.triage.activation import releases

    counts = {"releases": 0, "incidents": 0, "events": 0, "cases": 0}
    app_id = "support-triage"
    app = store.get("apps", app_id)
    recs = sorted(releases(), key=lambda r: r["proposed_at"])
    for r in recs:
        store.set("releases", r["release_id"], r)
        counts["releases"] += 1
        for kind, when, actor, reason in (
            (
                "release_proposed",
                r["proposed_at"],
                r["proposed_by"],
                f"Proposed {r['candidate_config_id']} with a {len(r['cohort'])}-intent cohort",
            ),
            (f"release_{r['decision']}", r["decided_at"], r["decided_by"], r["rationale"]),
        ):
            if not when:
                continue
            event_id = f"{r['release_id']}-{kind}"
            if store.get(f"apps/{app_id}/events", event_id) is None:
                store.create(
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
                        "evidence_refs": [f"artifacts/releases/{r['release_id']}.json"],
                        "created_at": when,
                    },
                )
                counts["events"] += 1
    decided = [r for r in recs if r["decision"]]
    if app and decided:
        last = decided[-1]
        evidence = {
            **(app.get("evidence") or {}),
            "release_decision": last["decision"],
            "release_ref": f"artifacts/releases/{last['release_id']}.json",
        }
        store.update(
            "apps", app_id, {"evidence": evidence, "last_decision": f"Release {last['decision']}"}
        )
    if INCIDENT_DIR.exists():
        for path in sorted(INCIDENT_DIR.glob("*.json")):
            inc = json.loads(path.read_text())
            store.set("incidents", inc["incident_id"], inc)
            counts["incidents"] += 1
    for path in sorted(MONITORING_DIR.glob("drill_*.json")) if MONITORING_DIR.exists() else []:
        drill = json.loads(path.read_text())
        for i, e in enumerate(drill["timeline"]):
            event_id = f"{path.stem}-{i}"
            if store.get(f"apps/{app_id}/events", event_id) is None:
                store.create(
                    f"apps/{app_id}/events",
                    event_id,
                    {
                        "event_id": event_id,
                        "app_id": app_id,
                        "kind": f"drill_{e['event']}",
                        "from_stage": None,
                        "to_stage": None,
                        "actor": e["actor"],
                        "reason": f"Simulated day {e['day']} (FIXTURE drill): {e['detail']}",
                        "evidence_refs": [f"artifacts/monitoring/{path.name}"],
                        "created_at": drill["ran_at"],
                    },
                )
                counts["events"] += 1
    runs = (
        sorted(p for p in SHADOW_DIR.glob("shadow_*") if (p / "comparisons.jsonl").exists())
        if SHADOW_DIR.exists()
        else []
    )
    if runs:
        rows = [json.loads(x) for x in (runs[-1] / "comparisons.jsonl").read_text().splitlines()]
        texts: dict[str, str] = {}
        try:
            from control_plane.triage.dataset import load_split

            texts = {c.case_id: c.text for c in load_split("shadow_pool")}
        except (FileNotFoundError, KeyError):
            texts = {}
        last_day = max(r["day"] for r in rows)
        for r in rows:
            if r["day"] == last_day and r["approved_route"] == "review":
                store.set(
                    "routed_cases",
                    r["case_id"],
                    {
                        "case_id": r["case_id"],
                        "day": r["day"],
                        "app_id": app_id,
                        "text": texts.get(r["case_id"]),
                        "suggested_label": r["approved_label"],
                        "shadow_llm_label": r["candidate_label"],
                        "status": "pending",
                        "provenance": "SIMULATED",
                    },
                )
                counts["cases"] += 1
    return counts
