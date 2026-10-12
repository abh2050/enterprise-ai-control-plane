"""Monitoring signals, alert policy, incidents, and the incident drill (Section 6.8).

Signals per simulated day, for the configuration that is authoritative in production:
review rate, cost per correctly handled case, and accuracy on a seeded 10% labeled
sample. Alert thresholds come from the baseline window (days 1 to 7) and are frozen into
a create-only alert policy before the drill runs. Shadow-derived signals are SIMULATED;
drill traffic is FIXTURE.

Rollback in this deployment means pausing automation: while paused, every case goes to
human review (the process before automation), and alerting on the paused config stops.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from control_plane.contracts import Route
from control_plane.triage.business_model import load_assumptions
from control_plane.triage.dataset import REPO_ROOT, Case
from control_plane.triage.gates import gate_config, write_json
from control_plane.triage.scorecard import CaseResult, total_cost_per_correct

MONITORING_DIR = REPO_ROOT / "artifacts" / "monitoring"
INCIDENT_DIR = REPO_ROOT / "artifacts" / "incidents"
SHADOW_DIR = REPO_ROOT / "artifacts" / "shadow"
DRIFT_PATH = REPO_ROOT / "data" / "drift_cases.jsonl"


class MonitoringError(RuntimeError):
    pass


def load_comparisons(run_id: str) -> list[dict[str, Any]]:
    path = SHADOW_DIR / run_id / "comparisons.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()]


def _sample(case_ids: list[str], day: int) -> set[str]:
    cfg = gate_config()["monitoring"]
    rng = np.random.default_rng(cfg["sample_seed"] + day)
    k = max(1, round(len(case_ids) * cfg["labeled_sample_rate"]))
    return {case_ids[i] for i in rng.choice(len(case_ids), size=k, replace=False)}


def day_signals(
    rows: list[dict[str, Any]], day: int, authority: str = "approved"
) -> dict[str, Any]:
    """Signals for one day. ``authority`` is "approved" (classifier) or "manual"."""
    econ = load_assumptions()[0].economics()
    from control_plane.triage.dataset import SENSITIVE_INTENTS

    if authority == "manual":
        results = [
            CaseResult(r["case_id"], r["reference_label"], None, Route.REVIEW, 0, 0) for r in rows
        ]
    else:
        results = [
            CaseResult(
                r["case_id"],
                r["reference_label"],
                r["approved_label"],
                Route(r["approved_route"]),
                2,
                0,
            )
            for r in rows
        ]
    sampled_ids = _sample([r["case_id"] for r in rows], day)
    sampled = [r for r in results if r.case_id in sampled_ids]
    # In manual mode a person labels every case, so sampled accuracy is not a model signal.
    accuracy = (
        None
        if authority == "manual"
        else sum(r.correct or r.route is not Route.AUTO for r in sampled) / len(sampled)
    )
    return {
        "day": day,
        "cases": len(rows),
        "authority": authority,
        "review_rate": sum(r.route is Route.REVIEW for r in results) / len(results),
        "cost_per_correct_usd": total_cost_per_correct(results, econ, frozenset(SENSITIVE_INTENTS)),
        "sampled_accuracy": accuracy,
        "sampled_cases": len(sampled),
        "drift_cases": sum(r["case_id"].startswith("drift-") for r in rows),
    }


def freeze_alert_policy(run_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Derive thresholds from the baseline window and freeze them (create only)."""
    now = now or datetime.now(UTC)
    cfg = gate_config()["monitoring"]
    first, last = cfg["baseline_days"]
    rows = load_comparisons(run_id)
    baseline = [day_signals([r for r in rows if r["day"] == d], d) for d in range(first, last + 1)]

    def stats(key: str) -> tuple[float, float]:
        values = [float(b[key]) for b in baseline]
        return statistics.mean(values), statistics.stdev(values)

    mean_rr, sd_rr = stats("review_rate")
    mean_c, sd_c = stats("cost_per_correct_usd")
    mean_a, sd_a = stats("sampled_accuracy")
    thresholds = {
        "review_rate": {
            "direction": "above",
            "value": max(mean_rr + 3 * sd_rr, mean_rr + 0.05),
            "baseline_mean": mean_rr,
            "baseline_sd": sd_rr,
        },
        "cost_per_correct_usd": {
            "direction": "above",
            "value": max(mean_c + 3 * sd_c, mean_c * 1.10),
            "baseline_mean": mean_c,
            "baseline_sd": sd_c,
        },
        "sampled_accuracy": {
            "direction": "below",
            "value": min(mean_a - 3 * sd_a, mean_a - 0.05),
            "baseline_mean": mean_a,
            "baseline_sd": sd_a,
        },
    }
    policy_id = f"alerts_{run_id}"
    path = MONITORING_DIR / f"{policy_id}.json"
    if path.exists():
        raise MonitoringError(f"{policy_id} is frozen and already exists")
    record = {
        "policy_id": policy_id,
        "shadow_run": run_id,
        "baseline_days": [first, last],
        "rules": cfg["signals"],
        "thresholds": thresholds,
        "frozen_at": now.isoformat(),
        "baseline_signals": baseline,
        "provenance": "SIMULATED",
    }
    write_json(path, record)
    return record


def breaches(signals: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key, t in thresholds.items():
        observed = signals.get(key)
        if observed is None:
            continue
        hit = observed > t["value"] if t["direction"] == "above" else observed < t["value"]
        if hit:
            out.append(
                {
                    "signal": key,
                    "observed": observed,
                    "threshold": t["value"],
                    "direction": t["direction"],
                }
            )
    return out


def load_drift() -> list[dict[str, Any]]:
    return [json.loads(x) for x in DRIFT_PATH.read_text().splitlines() if x.strip()]


def drift_rows(run_id: str, drift_calls: Any = None) -> list[dict[str, Any]]:
    """Classifier (and shadow candidate) results for the drift cases, spread over the drill days.

    ``drift_calls`` maps case_id to an LLMCall for the shadow candidate, when available.
    """
    from control_plane.contracts import ConfigKind
    from control_plane.triage.evaluate import POLICY_DIR, _policy_params, _read
    from control_plane.triage.policy import route
    from control_plane.triage.shadow import _classifier

    days = gate_config()["drill"]["days"]
    drift = load_drift()
    rng = np.random.default_rng(gate_config()["monitoring"]["sample_seed"])
    order = rng.permutation(len(drift))
    parts = np.array_split(order, len(days))
    params = _policy_params(_read(POLICY_DIR / "policy_classifier_v1.json"))
    preds = _classifier().predict([d["text"] for d in drift])
    rows = []
    for day, idxs in zip(days, parts, strict=True):
        for i in idxs:
            d, pred = drift[int(i)], preds[int(i)]
            r = route(params, ConfigKind.CLASSIFIER, pred.label, pred.prob)
            call = (drift_calls or {}).get(d["case_id"])
            rows.append(
                {
                    "day": day,
                    "case_id": d["case_id"],
                    "category": d["category"],
                    "reference_label": d["reference_label"],
                    "approved_label": pred.label,
                    "approved_prob": round(pred.prob, 6),
                    "approved_route": r.value,
                    "candidate_label": getattr(call, "llm_label", None),
                    "provenance": "FIXTURE",
                }
            )
    return rows


def run_drill(run_id: str, drift_calls: Any = None, now: datetime | None = None) -> dict[str, Any]:
    """Inject drift on the drill days, detect, pause, roll back, and recover."""
    now = now or datetime.now(UTC)
    policy_path = MONITORING_DIR / f"alerts_{run_id}.json"
    if not policy_path.exists():
        raise MonitoringError("freeze the alert policy before the drill: cp monitor freeze")
    policy = json.loads(policy_path.read_text())
    thresholds = policy["thresholds"]
    shadow = load_comparisons(run_id)
    drift = drift_rows(run_id, drift_calls)
    drill_days = gate_config()["drill"]["days"]
    started = time.perf_counter()

    timeline: list[dict[str, Any]] = []
    days: list[dict[str, Any]] = []
    authority = "approved"
    incident: dict[str, Any] | None = None
    for day in range(1, 15):
        rows = [r for r in shadow if r["day"] == day] + [r for r in drift if r["day"] == day]
        signals = day_signals(rows, day, authority)
        hits = breaches(signals, thresholds) if authority == "approved" else []
        # While automation is paused, check the approved config in shadow before resuming.
        check = day_signals(rows, day, "approved") if authority == "manual" else None
        check_hits = breaches(check, thresholds) if check else []
        days.append(
            {
                **signals,
                "breaches": hits,
                "shadow_check": check,
                "shadow_check_breaches": check_hits,
            }
        )
        if hits and incident is None:
            elapsed = time.perf_counter() - started
            incident = {
                "incident_id": f"drill_{run_id}",
                "app_id": "support-triage",
                "signal": hits[0]["signal"],
                "threshold": hits[0]["threshold"],
                "observed": hits[0]["observed"],
                "all_breaches": hits,
                "status": "open",
                "opened_day": day,
                "opened_at": now.isoformat(),
                "detection_delay_days": day - drill_days[0],
                "detection_processing_seconds": round(elapsed, 3),
                "actions": [],
                "closed_at": None,
                "provenance": "FIXTURE",
            }
            timeline.append(
                {
                    "day": day,
                    "event": "incident_opened",
                    "actor": "monitoring",
                    "detail": "; ".join(
                        f"{h['signal']} {h['observed']:.3f} vs {h['threshold']:.3f}" for h in hits
                    ),
                }
            )
            timeline.append(
                {
                    "day": day,
                    "event": "automation_paused",
                    "actor": "admin@example.com",
                    "detail": "Governance admin paused automation for Support Triage",
                }
            )
            timeline.append(
                {
                    "day": day,
                    "event": "rollback",
                    "actor": "admin@example.com",
                    "detail": "Rolled back to the prior process: every case routes to "
                    "human review until signals recover",
                }
            )
            incident["status"] = "mitigated"
            incident["actions"] = [t["detail"] for t in timeline[-2:]]
            authority = "manual"
        elif authority == "manual" and day > drill_days[-1] and not check_hits:
            authority = "approved"
            timeline.append(
                {
                    "day": day,
                    "event": "automation_resumed",
                    "actor": "admin@example.com",
                    "detail": "Shadow check within every threshold; automation resumed",
                }
            )
            if incident:
                incident["status"] = "closed"
                incident["closed_day"] = day
                incident["closed_at"] = now.isoformat()
                incident["actions"].append(timeline[-1]["detail"])
    record = {
        "run_id": run_id,
        "alert_policy": policy["policy_id"],
        "drill_days": drill_days,
        "drift_cases": len(drift),
        "days": days,
        "timeline": timeline,
        "incident": incident,
        "detected": incident is not None,
        "drift_rows": drift,
        "provenance": {"baseline_days": "SIMULATED", "drift_cases": "FIXTURE"},
        "ran_at": now.isoformat(),
    }
    write_json(MONITORING_DIR / f"drill_{run_id}.json", record)
    if incident:
        write_json(INCIDENT_DIR / f"{incident['incident_id']}.json", incident)
    return record


def latest(prefix: str) -> dict[str, Any] | None:
    if not MONITORING_DIR.exists():
        return None
    files = sorted(MONITORING_DIR.glob(f"{prefix}_*.json"))
    return json.loads(files[-1].read_text()) if files else None


__all__ = ["Case", "Path", "freeze_alert_policy", "run_drill"]
