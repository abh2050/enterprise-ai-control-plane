"""Release proposals, decisions, and cohort routing (Section 6.7).

- An app owner proposes a release: candidate, baseline, policy, cohort, and the gate
  results computed on the frozen evaluation set.
- A governance admin records one decision (activate_cohort, activate_full, withhold,
  reject) with a rationale and the scorecard reference. A decision is final.
- activate_full is refused unless every gate passes for the full candidate.
- activate_cohort is refused unless every gate passes for the blended cohort.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from control_plane.triage.dataset import REPO_ROOT
from control_plane.triage.evaluate import POLICY_DIR, FreezeError
from control_plane.triage.gates import (
    blend,
    blended_scorecard,
    evaluate_gates,
    gate_config,
    load_frozen,
    propose_cohort,
    write_json,
)

RELEASE_DIR = REPO_ROOT / "artifacts" / "releases"
APP_ID = "support-triage"
DECISIONS = ("activate_cohort", "activate_full", "withhold", "reject")


class ReleaseError(RuntimeError):
    pass


def authoritative(approved_label: str, cohort: Iterable[str] | None) -> str:
    """Which config decides a case: the candidate inside the cohort, else the approved one."""
    if cohort is None:
        return "candidate"
    return "candidate" if approved_label in set(cohort) else "approved"


def _gates_for(candidate_id: str, cohort: list[str] | None) -> dict[str, Any]:
    baseline_id = gate_config()["baseline_config"]
    approved = load_frozen(baseline_id)
    candidate = load_frozen(candidate_id)
    results, risk, _ = blend(approved, candidate, cohort)
    base_results, _, _ = blend(approved, approved, None)
    gates = evaluate_gates(results, risk, base_results, cohort)
    source = f"blend of {baseline_id} and {candidate_id} frozen results"
    return {
        "gates": gates,
        "all_passed": all(g["passed"] for g in gates),
        "scorecard": blended_scorecard(results, risk, source),
    }


def propose(
    candidate_id: str,
    proposed_by: str,
    cohort: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    baseline_id = gate_config()["baseline_config"]
    policy = json.loads((POLICY_DIR / f"policy_{candidate_id}.json").read_text())
    proposal = (
        cohort
        if cohort is not None
        else propose_cohort(load_frozen(candidate_id), policy["eligible_cohort"])["cohort"]
    )
    full = _gates_for(candidate_id, None)
    cohort_eval = _gates_for(candidate_id, proposal)
    release_id = f"rel_{candidate_id}_{now.strftime('%Y%m%dT%H%M%SZ')}"
    runs = json.loads((REPO_ROOT / "artifacts/experiments/frozen_runs.json").read_text())
    record = {
        "release_id": release_id,
        "app_id": APP_ID,
        "candidate_config_id": candidate_id,
        "baseline_config_id": baseline_id,
        "policy_id": policy["policy_id"],
        "cohort": proposal,
        "cohort_excluded": sorted(set(policy["eligible_cohort"]) - set(proposal)),
        "full_candidate": full,
        "cohort_candidate": cohort_eval,
        "evidence_refs": [
            f"artifacts/experiments/{runs[c]['experiment_id']}" for c in (baseline_id, candidate_id)
        ],
        "proposed_by": proposed_by,
        "proposed_at": now.isoformat(),
        "decision": None,
        "rationale": None,
        "decided_by": None,
        "decided_at": None,
        "shadow_ref": None,
        "provenance": "MEASURED",
    }
    path = RELEASE_DIR / f"{release_id}.json"
    if path.exists():
        raise ReleaseError(f"{release_id} already exists")
    write_json(path, record)
    return record


def load_release(release_id: str) -> dict[str, Any]:
    path = RELEASE_DIR / f"{release_id}.json"
    if not path.exists():
        raise ReleaseError(f"release {release_id} not found")
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def attach_shadow(release_id: str, shadow_ref: str) -> dict[str, Any]:
    record = load_release(release_id)
    if record["decision"]:
        raise ReleaseError("a decided release cannot change")
    record["shadow_ref"] = shadow_ref
    write_json(RELEASE_DIR / f"{release_id}.json", record)
    return record


def validate_decision(record: dict[str, Any], decision: str, rationale: str, role: str) -> None:
    """The decision rules, shared by the CLI and the console."""
    if role != "governance_admin":
        raise ReleaseError("only a governance admin records release decisions")
    if decision not in DECISIONS:
        raise ReleaseError(f"decision must be one of {DECISIONS}")
    if len(rationale.strip()) < 20:
        raise ReleaseError("a rationale of at least 20 characters is required")
    if record["decision"]:
        raise ReleaseError(f"{record['release_id']} was already decided: {record['decision']}")
    if decision == "activate_full" and not record["full_candidate"]["all_passed"]:
        failed = [g["gate"] for g in record["full_candidate"]["gates"] if not g["passed"]]
        raise ReleaseError(f"activate_full is blocked; failing gates: {failed}")
    if decision == "activate_cohort" and not record["cohort_candidate"]["all_passed"]:
        failed = [g["gate"] for g in record["cohort_candidate"]["gates"] if not g["passed"]]
        raise ReleaseError(f"activate_cohort is blocked; failing cohort gates: {failed}")


def decide(
    release_id: str,
    decision: str,
    rationale: str,
    decided_by: str,
    role: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    record = load_release(release_id)
    validate_decision(record, decision, rationale, role)
    record.update(
        decision=decision,
        rationale=rationale.strip(),
        decided_by=decided_by,
        decided_at=now.isoformat(),
    )
    write_json(RELEASE_DIR / f"{release_id}.json", record)
    return record


def build_proposal(
    candidate_id: str, proposed_by: str, cohort: list[str] | None, now: datetime
) -> dict[str, Any]:
    """A release record without writing it (the console stores its own proposals)."""
    baseline_id = gate_config()["baseline_config"]
    policy = json.loads((POLICY_DIR / f"policy_{candidate_id}.json").read_text())
    proposal = (
        cohort
        if cohort is not None
        else propose_cohort(load_frozen(candidate_id), policy["eligible_cohort"])["cohort"]
    )
    return {
        "release_id": f"rel_{candidate_id}_{now.strftime('%Y%m%dT%H%M%SZ')}",
        "app_id": APP_ID,
        "candidate_config_id": candidate_id,
        "baseline_config_id": baseline_id,
        "policy_id": policy["policy_id"],
        "cohort": proposal,
        "cohort_excluded": sorted(set(policy["eligible_cohort"]) - set(proposal)),
        "full_candidate": _gates_for(candidate_id, None),
        "cohort_candidate": _gates_for(candidate_id, proposal),
        "proposed_by": proposed_by,
        "proposed_at": now.isoformat(),
        "decision": None,
        "rationale": None,
        "decided_by": None,
        "decided_at": None,
        "shadow_ref": None,
        "provenance": "MEASURED",
    }


def preview(candidate_id: str, cohort: list[str]) -> dict[str, Any]:
    return _gates_for(candidate_id, cohort)


def latest_release(candidate_id: str | None = None) -> dict[str, Any] | None:
    """Most recently proposed release, optionally for one candidate config."""
    found = [
        r for r in releases() if candidate_id is None or r["candidate_config_id"] == candidate_id
    ]
    return max(found, key=lambda r: r["proposed_at"]) if found else None


def releases() -> list[dict[str, Any]]:
    if not RELEASE_DIR.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(RELEASE_DIR.glob("rel_*.json"))]


__all__ = ["FreezeError", "Path", "authoritative", "decide", "propose"]
