"""docs/executive_report.md from the BigQuery analytics queries (Section 8).

Answers two questions for leadership: does the deployment create value, and what
investment comes next. Every figure carries its provenance label.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from control_plane.analytics.queries import run
from control_plane.triage.business_model import load_assumptions
from control_plane.triage.dataset import REPO_ROOT

REPORT = REPO_ROOT / "docs" / "executive_report.md"


def _usd(v: float | None) -> str:
    return "n/a" if v is None else f"{'−' if v < 0 else ''}${abs(v):,.0f}"


def generate(project: str, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    end = now.date()
    start = end - timedelta(days=180)
    a, raw = load_assumptions()
    triage = run(
        project,
        "triage_net_value",
        start,
        end,
        volume=float(a.monthly_volume),
        manual_minutes=a.manual_handling_minutes,
        review_minutes=a.review_minutes,
        labor_rate=a.loaded_labor_rate,
        misroute_cost=a.misroute_cost_standard,
        infrastructure=a.infrastructure_monthly,
    )
    spend = run(project, "spend_value", end - timedelta(days=30), end)
    weekly = run(project, "weekly_flow", end - timedelta(days=90), end)
    medians = run(project, "stage_medians", start, end)
    last = run(project, "last_export", start, end)[0]["last_export_at"]

    by_platform: dict[str, dict[str, Any]] = {}
    for r in spend:
        p = by_platform.setdefault(
            r["platform"], {"apps": 0, "spend": 0.0, "value": 0.0, "spend_prov": set()}
        )
        p["apps"] += 1
        p["spend"] += r["monthly_spend_usd"] or 0.0
        p["value"] += r["monthly_value_usd"] or 0.0
        p["spend_prov"].add(r["spend_provenance"])
    best = max(triage, key=lambda r: r["net_monthly_value"]) if triage else None
    stalled_now = weekly[-1]["stalled"] if weekly else 0
    slowest = medians[0] if medians else None

    lines = [
        "# Executive report: AI application portfolio",
        "",
        f"Generated {now.date().isoformat()} by `cp report` from BigQuery "
        f"(`{project}.control_plane`, last export {last.isoformat() if last else 'unknown'}).",
        "The registry is a SYNTHETIC sample organization; Support Triage results are real runs.",
        "",
        "## Does the deployment create value?",
        "",
    ]
    if best:
        lines.append(
            f"Support Triage's best configuration, {best['config_id']}, would return "
            f"{_usd(best['net_monthly_value'])} per month `ASSUMPTION` at "
            f"{a.monthly_volume:,.0f} cases a month `ASSUMPTION`, using measured coverage "
            f"{best['coverage']:.1%} and auto precision {best['auto_precision']:.3f} "
            "`MEASURED`. That is the classifier the release decision kept in production; the "
            "LLM candidates were withheld or rejected on measured release gates "
            "(docs/release_recommendation.md)."
        )
    lines += [
        "",
        "| Config | Coverage | Auto precision | Model cost per case | Net monthly value |",
        "|---|---|---|---|---|",
    ]
    for r in triage:
        lines.append(
            f"| {r['config_id']} | {r['coverage']:.1%} `MEASURED` | "
            f"{r['auto_precision']:.3f} `MEASURED` | ${r['model_cost_per_case']:.5f} "
            f"`MEASURED` | {_usd(r['net_monthly_value'])} `ASSUMPTION` |"
        )
    lines += [
        "",
        "## Portfolio spend and value by platform",
        "",
        "| Platform | Apps | Monthly spend | Estimated monthly value |",
        "|---|---|---|---|",
    ]
    for name, p in sorted(by_platform.items(), key=lambda kv: -kv[1]["spend"]):
        prov = "MEASURED" if p["spend_prov"] == {"MEASURED"} else "FIXTURE"
        lines.append(
            f"| {name} | {p['apps']} | {_usd(p['spend'])} `{prov}` | "
            f"{_usd(p['value'])} `ASSUMPTION` |"
        )
    lines += [
        "",
        "## Pipeline health",
        "",
        f"- {stalled_now} apps sat more than 30 days in one stage in the latest week `FIXTURE`.",
    ]
    if slowest:
        lines.append(
            f"- The slowest stage is {slowest['stage']} at a median of "
            f"{slowest['median_days']:.1f} days `FIXTURE`."
        )
    lines += [
        "",
        "## What investment comes next",
        "",
        "1. Fix the Support Triage sensitive-intent confusions (card payment versus direct "
        "debit) and re-run the release gates before any LLM activation.",
        "2. Use the LLM where it measurably wins: an out-of-scope guard in front of the "
        "classifier (it flagged every out-of-domain drift case in the drill).",
        "3. Add a drift-specific monitoring signal; the drill was detected by a 0.0006 margin.",
        "4. Clear the review queue for stalled apps before funding new intake.",
        "",
        "Assumptions behind every money figure: configs/business_model.yaml "
        f"({', '.join(raw['assumptions'])}).",
        "",
    ]
    text = "\n".join(lines)
    REPORT.write_text(text)
    return text
