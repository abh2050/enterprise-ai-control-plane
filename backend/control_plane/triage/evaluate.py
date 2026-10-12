"""Training, freezing, and the frozen evaluation runner for Support Triage.

Order of operations, enforced with create-only artifact files:
1. ``train_classifier``: fit on the classifier training split, calibrate on dev.
2. ``freeze_classifier``: tune the threshold on dev, then create the policy and config.
3. ``evaluate_config``: run once on the frozen evaluation set. A second run needs an
   explicit reason, which is recorded next to the first run.

All configs see the frozen cases in the same shuffled order (seed 42).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from control_plane.contracts import ConfigKind, Provenance, Route
from control_plane.triage.dataset import (
    REPO_ROOT,
    SEED,
    SENSITIVE_INTENTS,
    Case,
    load_categories,
    load_manifest,
    load_split,
)
from control_plane.triage.policy import PolicyParams, route, tune_classifier_threshold
from control_plane.triage.scorecard import CaseResult, RiskResult, build_scorecard

ARTIFACTS = REPO_ROOT / "artifacts"
CONFIG_DIR = ARTIFACTS / "configs"
POLICY_DIR = ARTIFACTS / "policies"
EXPERIMENT_DIR = ARTIFACTS / "experiments"
FROZEN_RUNS = EXPERIMENT_DIR / "frozen_runs.json"
TRIAGE_CONFIGS = REPO_ROOT / "configs" / "triage_configs.yaml"
RISK_SUITE = REPO_ROOT / "data" / "risk_suite.jsonl"
APP_ID = "support-triage"


class FreezeError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_create_only(path: Path, data: Any) -> None:
    if path.exists():
        raise FreezeError(f"{path.relative_to(REPO_ROOT)} is create only and already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _read(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def triage_settings() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(TRIAGE_CONFIGS.read_text())
    return data


def load_risk_suite() -> list[dict[str, Any]]:
    return [json.loads(line) for line in RISK_SUITE.read_text().splitlines() if line.strip()]


def frozen_case_order(cases: list[Case]) -> list[Case]:
    """Identical shuffled order for every config."""
    rng = np.random.default_rng(SEED)
    return [cases[i] for i in rng.permutation(len(cases))]


# 1. Train


def train_classifier(name: str = "classifier_v1") -> dict[str, Any]:
    from control_plane.triage import classifier as clf_mod  # scikit-learn loads on use

    train = load_split("classifier_train")
    dev = load_split("dev")
    started = time.perf_counter()
    model = clf_mod.train(train, dev)
    path, digest = clf_mod.save(model, name)
    record = {
        "name": name,
        "model_sha256": digest,
        "hyperparameters": {
            k: list(v) if isinstance(v, tuple) else v for k, v in clf_mod.HYPERPARAMS.items()
        },
        "train_split_sha256": load_manifest()["splits"]["classifier_train"]["sha256"],
        "calibration_split_sha256": load_manifest()["splits"]["dev"]["sha256"],
        "train_rows": len(train),
        "calibration_rows": len(dev),
        "train_seconds": round(time.perf_counter() - started, 1),
        "trained_at": _now(),
    }
    (clf_mod.MODEL_DIR / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


# 2. Freeze policy and config


def freeze_classifier(config_id: str = "classifier_v1", created_by: str = "cli") -> dict[str, Any]:
    from control_plane.triage import classifier as clf_mod  # scikit-learn loads on use

    settings = triage_settings()
    spec = settings["configs"][config_id]
    tuning = settings["policy_tuning"]
    model_record = _read(clf_mod.MODEL_DIR / f"{spec['model']}.json")
    model = clf_mod.load(spec["model"], model_record["model_sha256"])

    dev = load_split("dev")
    preds = model.predict([c.text for c in dev])
    sensitive = frozenset(SENSITIVE_INTENTS)
    choice = tune_classifier_threshold(
        [p.label for p in preds],
        [p.prob for p in preds],
        [c.label for c in dev],
        sensitive,
        target_precision=tuning["target_dev_auto_precision"]["value"],
        min_auto=tuning["min_dev_auto_cases"]["value"],
    )
    policy_id = spec["policy_id"]
    policy = {
        "policy_id": policy_id,
        "thresholds": {"classifier_threshold": choice.threshold},
        "sensitive_intents": sorted(sensitive),
        "eligible_cohort": load_categories(),
        "tuning": {
            "split": "dev",
            "target_dev_auto_precision": tuning["target_dev_auto_precision"],
            "dev_auto_precision": choice.dev_auto_precision,
            "dev_coverage": choice.dev_coverage,
            "dev_auto_count": choice.dev_auto_count,
            "note": "Dev also calibrated the classifier, so dev precision is optimistic.",
        },
        "created_at": _now(),
    }
    config = {
        "config_id": config_id,
        "app_id": APP_ID,
        "version": spec["version"],
        "kind": ConfigKind.CLASSIFIER.value,
        "model_id": f"{spec['model']}@{model_record['model_sha256'][:12]}",
        "prompt_text": None,
        "prompt_sha256": None,
        "policy_id": policy_id,
        "limits": {},
        "price_card": None,
        "created_by": created_by,
        "created_at": _now(),
    }
    _write_create_only(POLICY_DIR / f"{policy_id}.json", policy)
    _write_create_only(CONFIG_DIR / f"{config_id}.json", config)
    return {"policy": policy, "config": config}


# 3. Evaluate


def _policy_params(policy: dict[str, Any]) -> PolicyParams:
    t = policy["thresholds"]
    return PolicyParams(
        classifier_threshold=t["classifier_threshold"],
        agreement_threshold=t.get("agreement_threshold"),
        sensitive_intents=frozenset(policy["sensitive_intents"]),
        eligible_cohort=frozenset(policy["eligible_cohort"]),
    )


def _guard_frozen_run(config_id: str, force_reason: str | None) -> dict[str, Any]:
    runs: dict[str, Any] = _read(FROZEN_RUNS) if FROZEN_RUNS.exists() else {}
    prior = runs.get(config_id)
    if prior and not force_reason:
        raise FreezeError(
            f"{config_id} already ran on the frozen set ({prior['experiment_id']}). "
            "Pass a reason to re-run; it will be recorded."
        )
    return runs


def evaluate_config(config_id: str, force_reason: str | None = None) -> dict[str, Any]:
    from control_plane.triage import classifier as clf_mod  # scikit-learn loads on use

    config_path = CONFIG_DIR / f"{config_id}.json"
    if not config_path.exists():
        raise FreezeError(f"{config_id} is not frozen yet; run `cp freeze {config_id}`")
    config = _read(config_path)
    policy = _read(POLICY_DIR / f"{config['policy_id']}.json")
    if config["kind"] != ConfigKind.CLASSIFIER.value:
        raise FreezeError("LLM configs are evaluated from M3")
    runs = _guard_frozen_run(config_id, force_reason)

    spec = triage_settings()["configs"][config_id]
    model_record = _read(clf_mod.MODEL_DIR / f"{spec['model']}.json")
    model = clf_mod.load(spec["model"], model_record["model_sha256"])
    params = _policy_params(policy)
    labels = load_categories()

    started_at = _now()
    cases = frozen_case_order(load_split("frozen_eval"))
    rows: list[dict[str, Any]] = []
    results: list[CaseResult] = []
    for case in cases:
        t0 = time.perf_counter()
        pred = model.predict([case.text])[0]
        latency_ms = max(1, round((time.perf_counter() - t0) * 1000))
        r = route(params, ConfigKind.CLASSIFIER, pred.label, pred.prob)
        result = CaseResult(case.case_id, case.label, pred.label, r, latency_ms, 0)
        results.append(result)
        rows.append(
            {
                "case_id": case.case_id,
                "predicted_label": pred.label,
                "reference_label": case.label,
                "route": r.value,
                "correct": result.correct,
                "classifier_prob": round(pred.prob, 6),
                "latency_ms": latency_ms,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_micros": 0,
                "attempt_count": 1,
            }
        )

    risk_rows = []
    risk_results = []
    for item in load_risk_suite():
        pred = model.predict([item["text"]])[0]
        r = route(params, ConfigKind.CLASSIFIER, pred.label, pred.prob)
        expected = Route(item["expected_route"])
        risk_results.append(RiskResult(item["case_id"], item["category"], expected, r))
        risk_rows.append(
            {
                "case_id": item["case_id"],
                "category": item["category"],
                "expected_route": expected.value,
                "route": r.value,
                "predicted_label": pred.label,
                "classifier_prob": round(pred.prob, 6),
            }
        )

    experiment_id = f"exp_{config_id}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    source = f"artifacts/experiments/{experiment_id}/results.jsonl"
    card = build_scorecard(
        results, labels, params.sensitive_intents, risk_results, Provenance.MEASURED, source
    )
    out = EXPERIMENT_DIR / experiment_id
    out.mkdir(parents=True, exist_ok=False)
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "risk_results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in risk_rows))
    (out / "scorecard.json").write_text(
        json.dumps({k: v.model_dump() for k, v in card.items()}, indent=2) + "\n"
    )
    experiment = {
        "experiment_id": experiment_id,
        "config_id": config_id,
        "policy_id": policy["policy_id"],
        "dataset_id": "banking77_frozen_eval",
        "dataset_sha256": load_manifest()["splits"]["frozen_eval"]["sha256"],
        "case_order_seed": SEED,
        "status": "finished",
        "cost_micros": 0,
        "started_at": started_at,
        "finished_at": _now(),
        "provenance": Provenance.MEASURED.value,
        "rerun_reason": force_reason,
    }
    (out / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")

    history = runs.get(config_id, {}).get("history", [])
    history.append({"experiment_id": experiment_id, "reason": force_reason or "first run"})
    runs[config_id] = {"experiment_id": experiment_id, "history": history}
    FROZEN_RUNS.parent.mkdir(parents=True, exist_ok=True)
    FROZEN_RUNS.write_text(json.dumps(runs, indent=2) + "\n")
    return {"experiment": experiment, "scorecard": card, "results": [asdict(r) for r in results]}
