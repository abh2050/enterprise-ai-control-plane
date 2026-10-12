"""Static snapshot export for the read-only console (console spec Section 9).

Calls the real API in process with a fixed clock and the SYNTHETIC seed, then writes
each read endpoint's JSON to a folder the snapshot build serves. The snapshot holds no
credentials and no write endpoint: it is static files only.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.fixtures import seed_registry
from control_plane.settings import Settings
from control_plane.store import MemoryStore

PLATFORMS = ["", "abacus", "copilot", "custom", "managed"]
RANGES = [30, 90, 180]
READ_PERMISSIONS = [
    "read_portfolio",
    "read_flow",
    "read_reports",
    "read_app_detail",
    "read_reviews",
    "read_incidents",
]


def query(params: dict[str, Any]) -> str:
    """Same rules as the frontend's query(): insertion order, empty values dropped."""
    parts = [f"{k}={v}" for k, v in params.items() if v not in (None, "")]
    return f"?{'&'.join(parts)}" if parts else ""


def file_name(path: str) -> str:
    """Mirror of snapshotFile() in frontend/src/lib/api.ts."""
    name = path.lstrip("/")
    for ch in "/?=&":
        name = name.replace(ch, "_")
    return f"{name or 'root'}.json"


def export(out_dir: Path, fixed_now: datetime) -> int:
    store = MemoryStore()
    seed_registry(store, fixed_now)
    app = create_app(Settings(_env_file=None, fixed_now=fixed_now), store)
    client = TestClient(app, client=("127.0.0.1", 5000))
    headers = {"X-Fixture-User": "admin@example.com"}
    target = out_dir / "snapshot"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    written = 0

    def save(path: str, body: Any) -> None:
        nonlocal written
        (target / file_name(path)).write_text(json.dumps(body))
        written += 1

    def get(path: str) -> Any:
        r = client.get(f"/api{path}", headers=headers)
        r.raise_for_status()
        return r.json()

    save("/mode", get("/mode"))
    save(
        "/me",
        {
            "email": "snapshot viewer",
            "role": "executive_viewer",
            "permissions": READ_PERMISSIONS,
            "security_reviewer": False,
        },
    )
    save(
        "/meta",
        {
            "generated_at": fixed_now.isoformat(),
            "note": "Static snapshot of the SYNTHETIC registry and measured experiment "
            "evidence. Read only.",
        },
    )
    for platform in PLATFORMS:
        for rng in RANGES:
            p = query({"platform": platform, "range": rng})
            save(f"/portfolio{p}", get(f"/portfolio{p}"))
            save(f"/flow{p}", get(f"/flow{p}"))
        p = query({"platform": platform})
        save(f"/portfolio/spend{p}", get(f"/portfolio/spend{p}"))
    apps = get("/apps?include_moves=false")
    save("/apps", apps)  # the snapshot client filters and sorts this list locally
    for a in apps:
        save(f"/apps/{a['app_id']}", get(f"/apps/{a['app_id']}"))
        save(f"/apps/{a['app_id']}/evidence", get(f"/apps/{a['app_id']}/evidence"))
    save("/assist", get("/assist"))
    save("/reviews/pending", get("/reviews/pending"))
    save("/incidents", get("/incidents"))
    return written
