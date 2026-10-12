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
