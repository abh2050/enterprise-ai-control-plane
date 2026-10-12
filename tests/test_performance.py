"""Console spec Section 9A budget: Portfolio API p95 <= 600 ms for 1,000 apps.

The load fixture clones the 40-app SYNTHETIC seed 25 times (1,000 apps, about 4,500
events) and times the Portfolio endpoint in process.
"""

import statistics
import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.assist import score_all
from control_plane.fixtures import seed_registry
from control_plane.settings import Settings
from control_plane.store import MemoryStore

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)


def thousand_app_store() -> MemoryStore:
    base = MemoryStore()
    seed_registry(base, NOW)
    store = MemoryStore()
    for u in base.list("users"):
        store.set("users", u["email"], u)
    for copy in range(25):
        for a in base.list("apps"):
            app_id = f"{a['app_id']}-{copy}"
            store.set("apps", app_id, {**a, "app_id": app_id})
            for e in base.list(f"apps/{a['app_id']}/events"):
                eid = f"{e['event_id']}-{copy}"
                store.create(f"apps/{app_id}/events", eid, {**e, "event_id": eid, "app_id": app_id})
    score_all(store, NOW)
    return store


def test_portfolio_p95_under_600ms_for_1000_apps() -> None:
    store = thousand_app_store()
    assert len(store.list("apps")) == 1000
    client = TestClient(
        create_app(Settings(_env_file=None, fixed_now=NOW), store), client=("127.0.0.1", 5000)
    )
    headers = {"X-Fixture-User": "admin@example.com"}
    timings = []
    for _ in range(20):
        start = time.perf_counter()
        r = client.get("/api/portfolio", headers=headers)
        timings.append((time.perf_counter() - start) * 1000)
        assert r.status_code == 200
    p95 = sorted(timings)[int(0.95 * len(timings)) - 1]
    print(f"portfolio 1,000 apps: median {statistics.median(timings):.0f} ms, p95 {p95:.0f} ms")
    assert p95 <= 600
