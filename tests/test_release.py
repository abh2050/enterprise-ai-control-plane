"""Required tests 9 and 10: release gating and cohort routing, on the real frozen results."""

import json
from pathlib import Path

import pytest

from control_plane.triage import activation
from control_plane.triage.dataset import SENSITIVE_INTENTS
from control_plane.triage.gates import blend, load_frozen

pytestmark = pytest.mark.skipif(
    not Path("artifacts/experiments/frozen_runs.json").exists(), reason="needs M3 artifacts"
)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(activation, "RELEASE_DIR", tmp_path)
    return tmp_path


def test_failed_gate_blocks_full_activation(sandbox) -> None:  # type: ignore[no-untyped-def]
    record = activation.propose("llm_high_capability_v1", "owner@example.com")
    assert not record["full_candidate"]["all_passed"]
    with pytest.raises(activation.ReleaseError, match="activate_full is blocked"):
        activation.decide(
            record["release_id"], "activate_full", "x" * 30, "admin@example.com", "governance_admin"
        )
    with pytest.raises(activation.ReleaseError, match="activate_cohort is blocked"):
        activation.decide(
            record["release_id"],
            "activate_cohort",
            "x" * 30,
            "admin@example.com",
            "governance_admin",
        )
    with pytest.raises(activation.ReleaseError, match="governance admin"):
        activation.decide(
            record["release_id"], "withhold", "x" * 30, "owner@example.com", "app_owner"
        )
    done = activation.decide(
        record["release_id"],
        "withhold",
        "Gates fail on measured data.",
        "admin@example.com",
        "governance_admin",
    )
    assert done["decision"] == "withhold"
    with pytest.raises(activation.ReleaseError, match="already decided"):
        activation.decide(
            record["release_id"], "reject", "x" * 30, "admin@example.com", "governance_admin"
        )
    saved = json.loads((sandbox / f"{record['release_id']}.json").read_text())
    assert saved["decision"] == "withhold" and saved["decided_by"] == "admin@example.com"


def test_cohort_excludes_failing_sensitive_intents(sandbox) -> None:  # type: ignore[no-untyped-def]
    record = activation.propose("llm_high_capability_v1", "owner@example.com")
    excluded = set(record["cohort_excluded"])
    assert excluded <= set(SENSITIVE_INTENTS)
    for gate in record["full_candidate"]["gates"]:
        if gate["gate"].startswith("sensitive_recall.") and not gate["passed"]:
            assert gate["gate"].split(".", 1)[1] in excluded


def test_cases_outside_the_cohort_stay_on_the_approved_config() -> None:
    approved = load_frozen("classifier_v1")
    candidate = load_frozen("llm_high_capability_v1")
    cohort = {"card_arrival", "exchange_rate", "top_up_failed"}
    _, _, rows = blend(approved, candidate, cohort)
    by_id = {r["case_id"]: r for r in approved.rows}
    cand = {r["case_id"]: r for r in candidate.rows}
    inside = outside = 0
    for row in rows:
        a = by_id[row["case_id"]]
        if a["predicted_label"] in cohort:
            inside += 1
            assert row["authority"] == "llm_high_capability_v1"
            assert row["route"] == cand[row["case_id"]]["route"]
        else:
            outside += 1
            assert row["authority"] == "classifier_v1"
            assert row["route"] == a["route"] and row["predicted_label"] == a["predicted_label"]
    assert inside > 0 and outside > 0
    assert activation.authoritative("card_arrival", cohort) == "candidate"
    assert activation.authoritative("compromised_card", cohort) == "approved"
