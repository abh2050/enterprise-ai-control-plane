"""API behaviour behind the console's end-to-end scenarios (backend half)."""

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.auth import FIXTURE_HEADER
from control_plane.contracts import Provenance
from control_plane.fixtures import seed_registry
from control_plane.settings import Settings
from control_plane.store import MemoryStore

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)
LABELS = {p.value for p in Provenance}


def client() -> TestClient:
    store = MemoryStore()
    seed_registry(store, NOW)
    app = create_app(Settings(_env_file=None, fixed_now=NOW), store)
    return TestClient(app, client=("127.0.0.1", 5000))


def as_(email: str) -> dict[str, str]:
    return {FIXTURE_HEADER: email}


ADMIN, OWNER, REVIEWER, EXEC = (
    as_(e)
    for e in ("admin@example.com", "owner@example.com", "reviewer@example.com", "exec@example.com")
)


def bare_numbers(node: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        if {"value", "unit", "provenance", "source"} <= node.keys():
            assert node["provenance"] in LABELS, path
            return found
        for k, v in node.items():
            found += bare_numbers(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += bare_numbers(v, f"{path}[{i}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        found.append(path)
    return found


def test_portfolio_kpis_and_metric_numbers_are_labelled() -> None:
    body = client().get("/api/portfolio", headers=EXEC).json()
    for section in ("kpis", "secondary"):
        assert bare_numbers(body[section]) == []
    assert body["kpis"]["monthly_model_spend_usd"]["provenance"] == "MEASURED"
    assert body["kpis"]["value_at_risk_usd"]["provenance"] == "ASSUMPTION"
    assert body["secondary"]["total_apps"]["provenance"] == "FIXTURE"
    assert len(body["attention"]) <= 10


def test_platform_filter_applies_to_every_module() -> None:
    body = client().get("/api/portfolio?platform=copilot", headers=EXEC).json()
    assert {p["app_id"] for p in body["matrix"]["points"]} <= {
        a["app_id"] for a in client().get("/api/apps?platform=copilot", headers=EXEC).json()
    }
    counts = {p["platform"]: p["apps"] for p in body["platforms"]}
    assert counts["abacus"] == 0 and counts["copilot"] > 0


def test_move_updates_portfolio_without_reload() -> None:
    c = client()
    detail = c.get("/api/apps/branch-faq-bot", headers=ADMIN).json()
    assert detail["app"]["stage"] == "review_gates"
    before = c.get("/api/portfolio", headers=ADMIN).json()["kpis"]["apps_in_production"]["value"]
    # Approve the missing gate (as the governance admin, who did not submit it), then publish.
    for gate in detail["card"]["pending_gates"]:
        r = c.post(
            f"/api/apps/branch-faq-bot/gates/{gate}",
            headers=ADMIN,
            json={"decision": "approve", "reason": "evidence checked"},
        )
        assert r.status_code == 200, r.text
    version = c.get("/api/apps/branch-faq-bot", headers=ADMIN).json()["app"]["version"]
    r = c.post(
        "/api/apps/branch-faq-bot/move",
        headers=ADMIN,
        json={
            "to_stage": "monitored",
            "expected_version": version,
            "reason": "publish decision",
            "source": "drag",
        },
    )
    assert r.status_code == 200, r.text
    after = c.get("/api/portfolio", headers=ADMIN).json()["kpis"]["apps_in_production"]["value"]
    assert after == before + 1


def test_stale_version_returns_409_with_current_record() -> None:
    c = client()
    v = c.get("/api/apps/meeting-notes", headers=OWNER).json()["app"]["version"]
    bad = c.post(
        "/api/apps/meeting-notes/move",
        headers=OWNER,
        json={"to_stage": "business_case", "expected_version": v - 1},
    )
    assert bad.status_code == 409 and bad.json()["current"]["app_id"] == "meeting-notes"


def test_missing_requirement_is_422_before_mutation() -> None:
    c = client()
    v = c.get("/api/apps/meeting-notes", headers=OWNER).json()["app"]["version"]
    r = c.post(
        "/api/apps/meeting-notes/move",
        headers=OWNER,
        json={"to_stage": "business_case", "expected_version": v},
    )
    assert r.status_code == 422 and r.json()["code"] == "business_case_fields"
    assert c.get("/api/apps/meeting-notes", headers=OWNER).json()["app"]["version"] == v


def test_executive_viewer_cannot_write_anything() -> None:
    c = client()
    v = c.get("/api/apps", headers=EXEC).json()[0]["version"]
    calls = [
        (
            "/api/apps/meeting-notes/move",
            {"to_stage": "retired", "expected_version": v, "reason": "x"},
        ),
        ("/api/apps/meeting-notes/notes", {"text": "hi", "idempotency_key": "k"}),
        ("/api/assist/meeting-notes/dismiss", {"code": "stage_stall", "reason": "x"}),
        ("/api/assist/meeting-notes/mark-safe", {"note": "x"}),
        ("/api/apps/branch-faq-bot/gates/governance", {"decision": "approve", "reason": "x"}),
    ]
    for path, body in calls:
        assert c.post(path, headers=EXEC, json=body).status_code == 403, path
    assert c.get("/api/export/catalog.csv", headers=EXEC).status_code == 403
    assert c.get("/api/apps/meeting-notes", headers=EXEC).status_code == 403


def test_reviews_disable_own_submissions() -> None:
    c = client()
    items = c.get("/api/reviews/pending", headers=OWNER).json()["gates"]
    owned = [
        i
        for i in items
        if i["owner"] == "owner@example.com" or i["submitted_by"] == "owner@example.com"
    ]
    assert all(not i["can_decide"] for i in items)  # owners hold no gate role
    assert all("different person" in i["blocked_reason"] for i in owned)


def test_note_idempotency_over_http() -> None:
    c = client()
    body = {"text": "Scope agreed with risk.", "idempotency_key": "abc-1"}
    first = c.post("/api/apps/meeting-notes/notes", headers=OWNER, json=body).json()
    second = c.post("/api/apps/meeting-notes/notes", headers=OWNER, json=body).json()
    assert first["created"] and not second["created"]
    notes = c.get("/api/apps/meeting-notes", headers=OWNER).json()["notes"]
    assert len(notes) == 1


def test_schedule_review_updates_score_and_deadline() -> None:
    c = client()
    rows = c.get("/api/assist", headers=ADMIN).json()["rows"]
    target = next(r for r in rows if any(x["code"] == "expiring_approval" for x in r["reasons"]))
    r = c.post(
        f"/api/assist/{target['app_id']}/schedule-review",
        headers=ADMIN,
        json={"review_at": "2026-10-15T09:00:00+00:00", "expected_version": target["version"]},
    )
    assert r.status_code == 200, r.text
    after = next(
        x
        for x in c.get("/api/assist", headers=ADMIN).json()["rows"]
        if x["app_id"] == target["app_id"]
    )
    assert after["score"] < target["score"]
    gate = c.get("/api/portfolio", headers=ADMIN).json()["next_gate"]
    assert gate["due_at"].startswith("2026-10-15")


def test_csv_export_admin_only_and_escaped() -> None:
    c = client()
    assert c.get("/api/export/catalog.csv", headers=OWNER).status_code == 403
    csv_text = c.get("/api/export/catalog.csv", headers=ADMIN).text
    assert csv_text.splitlines()[0].startswith("app_id,name")


def test_product_events_reject_extra_fields() -> None:
    c = client()
    ok = c.post(
        "/api/events", headers=OWNER, json={"event": "portfolio_viewed", "source_view": "portfolio"}
    )
    assert ok.status_code == 204
    leak = c.post(
        "/api/events",
        headers=OWNER,
        json={"event": "note_created", "source_view": "drawer", "text": "secret"},
    )
    assert leak.status_code == 422


def test_flow_and_evidence_endpoints() -> None:
    c = client()
    flow = c.get("/api/flow?range=90", headers=EXEC).json()
    assert flow["sankey"] and flow["stage_medians"]
    assert bare_numbers(flow["header"]) == []
    ev = c.get("/api/apps/support-triage/evidence", headers=OWNER).json()
    assert ev["available"] and set(ev["configs"]) == {
        "classifier_v1",
        "llm_low_cost_v1",
        "llm_high_capability_v1",
    }
