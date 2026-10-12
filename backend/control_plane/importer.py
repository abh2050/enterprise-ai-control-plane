"""Import an organization's app list from a CSV export (Section 5 importer).

A YAML mapping names the CSV column for each control plane field. Every row is
validated first; nothing is written unless all rows pass. Imported apps enter intake
with an event. Imported usage figures carry the provenance given in the mapping
(default ASSUMPTION). Real exports stay out of the repository (imports/ is gitignored).
"""

from __future__ import annotations

import csv
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from control_plane.registry import load_lifecycle, word_count
from control_plane.store import Store

REQUIRED = ["name", "business_unit", "platform", "risk_tier", "business_problem"]
OPTIONAL = ["owner", "monthly_spend_usd", "monthly_budget_usd", "monthly_volume", "active_users"]
PLATFORMS = {
    "abacus": "abacus",
    "copilot": "copilot",
    "microsoft copilot": "copilot",
    "custom": "custom",
    "custom build": "custom",
    "managed": "managed",
}
RISKS = {"low": "low", "medium": "medium", "med": "medium", "high": "high"}


@dataclass
class ImportReport:
    rows: int = 0
    created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or uuid.uuid4().hex[:8]


def _number(value: str, row: int, column: str, errors: list[str]) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        errors.append(f"row {row}: {column} is not a number: {value!r}")
        return None


def import_csv(
    store: Store, csv_path: Path, mapping_path: Path, actor: str, now: datetime | None = None
) -> ImportReport:
    now = now or datetime.now(UTC)
    mapping: dict[str, Any] = yaml.safe_load(mapping_path.read_text())
    provenance = mapping.pop("usage_provenance", "ASSUMPTION")
    missing = [f for f in REQUIRED if f not in mapping]
    report = ImportReport()
    if missing:
        report.errors.append(f"mapping is missing required fields: {missing}")
        return report
    min_words = load_lifecycle().raw["intake"]["min_problem_words"]
    existing = {a["app_id"] for a in store.list("apps")}
    records: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        absent = [c for f, c in mapping.items() if c not in (reader.fieldnames or [])]
        if absent:
            report.errors.append(f"CSV has no columns named {absent}")
            return report
        for i, raw in enumerate(reader, start=2):
            report.rows += 1
            row = {f: (raw.get(c) or "").strip() for f, c in mapping.items()}
            for f in REQUIRED:
                if not row.get(f):
                    report.errors.append(f"row {i}: {f} is empty")
            platform = PLATFORMS.get(row.get("platform", "").lower())
            risk = RISKS.get(row.get("risk_tier", "").lower())
            if row.get("platform") and not platform:
                report.errors.append(f"row {i}: unknown platform {row['platform']!r}")
            if row.get("risk_tier") and not risk:
                report.errors.append(f"row {i}: unknown risk tier {row['risk_tier']!r}")
            if row.get("business_problem") and word_count(row["business_problem"]) < min_words:
                report.errors.append(f"row {i}: business problem needs at least {min_words} words")
            spend = _number(row.get("monthly_spend_usd", ""), i, "monthly_spend_usd", report.errors)
            budget = _number(
                row.get("monthly_budget_usd", ""), i, "monthly_budget_usd", report.errors
            )
            volume = _number(row.get("monthly_volume", ""), i, "monthly_volume", report.errors)
            users = _number(row.get("active_users", ""), i, "active_users", report.errors)
            app_id = _slug(row.get("name", ""))
            while app_id in existing:
                app_id = f"{app_id}-{uuid.uuid4().hex[:4]}"
            existing.add(app_id)
            records.append(
                {
                    "app_id": app_id,
                    "name": row.get("name", ""),
                    "owner": row.get("owner") or None,
                    "business_unit": row.get("business_unit", ""),
                    "platform": platform or "custom",
                    "business_problem": row.get("business_problem", ""),
                    "risk_tier": risk or "low",
                    "stage": "intake",
                    "prior_stage": None,
                    "paused": False,
                    "version": 1,
                    "monthly_budget_micros": int((budget or 0) * 1e6),
                    "monthly_spend_micros": int((spend or 0) * 1e6),
                    "monthly_volume": int(volume) if volume is not None else None,
                    "active_users": int(users) if users is not None else None,
                    "usage_series": [],
                    "gates": {},
                    "evidence": {},
                    "usage_provenance": provenance,
                    "last_activity_at": now.isoformat(),
                    "stage_entered_at": now.isoformat(),
                    "created_at": now.isoformat(),
                    "provenance": "IMPORTED",
                }
            )
    if report.errors:
        return report  # all or nothing
    for rec in records:
        store.create("apps", rec["app_id"], rec)
        event_id = uuid.uuid4().hex
        store.create(
            f"apps/{rec['app_id']}/events",
            event_id,
            {
                "event_id": event_id,
                "app_id": rec["app_id"],
                "kind": "created",
                "from_stage": None,
                "to_stage": "intake",
                "actor": actor,
                "reason": f"Imported from {csv_path.name}",
                "evidence_refs": [],
                "created_at": now.isoformat(),
            },
        )
        report.created.append(rec["app_id"])
    return report
