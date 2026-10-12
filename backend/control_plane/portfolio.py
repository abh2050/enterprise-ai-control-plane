"""Portfolio, catalog, and Flow aggregates (console spec Section 9).

Provenance rules (docs/decisions.md D24):
- Numbers derived from the SYNTHETIC registry seed carry FIXTURE.
- Estimated value always carries ASSUMPTION.
- Model spend from settled ledger attempts carries MEASURED.
- A figure mixing sources takes the weakest label.
"""

from __future__ import annotations

import csv
import io
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from control_plane.assist import days_in_stage, is_stalled, stage_durations, stage_medians
from control_plane.contracts import Metric, Provenance
from control_plane.fixtures import ledger_summary
from control_plane.registry import Lifecycle, gates_approved, load_lifecycle, pending_gate_items
from control_plane.store import Store

PRODUCTION = "monitored"
LIVE_STAGES = {"monitored", "controlled_activation", "paused"}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


def metric(value: float | int | None, unit: str, provenance: Provenance, source: str) -> Metric:
    return Metric(value=value, unit=unit, provenance=provenance, source=source)


@dataclass
class Filters:
    platform: str | None = None
    range_days: int = 90


@dataclass
class Context:
    store: Store
    now: datetime
    filters: Filters = field(default_factory=Filters)
    lc: Lifecycle = field(default_factory=load_lifecycle)

    def __post_init__(self) -> None:
        all_apps = self.store.list("apps")
        self.events = [e for a in all_apps for e in self.store.list(f"apps/{a['app_id']}/events")]
        self.medians = stage_medians(self.events)
        self.apps = [
            a
            for a in all_apps
            if not self.filters.platform or a["platform"] == self.filters.platform
        ]
        ids = {a["app_id"] for a in self.apps}
        self.app_events = [e for e in self.events if e["app_id"] in ids]
        self.incidents = [i for i in self.store.list("incidents") if i["app_id"] in ids]
        self.open_incident_apps = {i["app_id"] for i in self.incidents if i["status"] == "open"}
        self.scores = {s["app_id"]: s for s in self.store.list("assist_scores")}
        self.users = {u["email"]: u for u in self.store.list("users")}
        month = self.now.strftime("%Y-%m")
        self.measured_spend = {
            app_id: v["committed_micros"]
            for app_id, v in ledger_summary().get("months", {}).get(month, {}).items()
        }

    def provenance(self, app: dict[str, Any]) -> Provenance:
        return (
            Provenance.FIXTURE
            if app.get("provenance") in ("SYNTHETIC", "FIXTURE")
            else Provenance.MEASURED
        )

    def spend_micros(self, app: dict[str, Any]) -> tuple[int, Provenance, str]:
        """Measured ledger spend for managed apps that have it, else imported spend."""
        if app["app_id"] in self.measured_spend:
            return (
                self.measured_spend[app["app_id"]],
                Provenance.MEASURED,
                "artifacts/ledger_summary.json",
            )
        return (
            app.get("monthly_spend_micros") or 0,
            self.provenance(app),
            f"apps/{app['app_id']}.monthly_spend_micros",
        )


def value_usd(app: dict[str, Any]) -> float | None:
    case = app.get("business_case") or {}
    v = (case.get("monthly_value_usd") or {}).get("value")
    return float(v) if v is not None else None


def health(app: dict[str, Any], ctx: Context) -> tuple[str, str]:
    """Return (status, rule label) from configs/lifecycle.yaml; first match wins."""
    rules = ctx.lc.raw["health"]
    owner = app.get("owner")
    owner_active = bool(owner and ctx.users.get(owner, {}).get("active", False))
    spend, _, _ = ctx.spend_micros(app)
    budget = app.get("monthly_budget_micros") or 0
    danger = {
        "open_incident": app["app_id"] in ctx.open_incident_apps,
        "over_budget": bool(budget) and spend > budget,
        "no_owner": not owner_active,
    }
    for r in rules["danger"]:
        if danger[r["rule"]]:
            return "danger", r["label"]
    expires = _parse(app.get("approvals_expire_at"))
    warning = {
        "no_business_case": app["stage"] not in ("intake", "retired")
        and not app.get("business_case"),
        "approvals_lapsed": app["stage"] in LIVE_STAGES
        and (
            not gates_approved(app, ctx.lc, ctx.now) or (expires is not None and expires < ctx.now)
        ),
    }
    for r in rules["warning"]:
        if warning[r["rule"]]:
            return "warning", r["label"]
    return "healthy", rules["healthy_label"]


def _live(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in apps if a["stage"] != "retired"]


def card(app: dict[str, Any], ctx: Context) -> dict[str, Any]:
    prov = ctx.provenance(app)
    spend, spend_prov, spend_src = ctx.spend_micros(app)
    status, rule = health(app, ctx)
    score = ctx.scores.get(app["app_id"], {})
    deadline = _next_deadline_for(app, ctx.now)
    days = days_in_stage(app, ctx.now)
    return {
        "app_id": app["app_id"],
        "name": app["name"],
        "owner": app.get("owner"),
        "business_unit": app["business_unit"],
        "platform": app["platform"],
        "stage": app["stage"],
        "risk_tier": app["risk_tier"],
        "version": app.get("version", 1),
        "business_problem": app["business_problem"],
        "days_in_stage": metric(int(days), "days", prov, f"apps/{app['app_id']}.stage_entered_at"),
        "stall_warning": app["stage"] != "retired"
        and days > ctx.lc.raw["stall"]["card_warning_days"],
        "stalled_vs_median": is_stalled(app, ctx.medians, ctx.lc, ctx.now),
        "monthly_spend_usd": metric(spend / 1e6, "USD/month", spend_prov, spend_src),
        "monthly_budget_usd": (app.get("monthly_budget_micros") or 0) / 1e6,
        "estimated_value_usd": metric(
            value_usd(app),
            "USD/month",
            Provenance.ASSUMPTION,
            f"apps/{app['app_id']}.business_case",
        ),
        "usage_series": app.get("usage_series") or [],
        "health": status,
        "health_rule": rule,
        "last_decision": app.get("last_decision"),
        "last_activity_at": app.get("last_activity_at"),
        "next_gate": deadline,
        "assist_score": score.get("score", 0.0),
        "assist_flagged": score.get("flagged", False),
        "pending_gates": pending_gate_items(app, ctx.lc),
        "submitted_by": app.get("submitted_by"),
        "provenance": app.get("provenance"),
    }


def _next_deadline_for(app: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    if app["stage"] == "retired":
        return None
    options = []
    expires = _parse(app.get("approvals_expire_at"))
    if expires and expires >= now:
        options.append(("approval_expires", expires))
    review = _parse(app.get("next_review_at"))
    if review and review >= now:
        options.append(("scheduled_review", review))
    if not options:
        return None
    kind, when = min(options, key=lambda o: o[1])
    return {"kind": kind, "due_at": when.isoformat()}


def catalog(
    ctx: Context,
    *,
    q: str | None = None,
    stage: str | None = None,
    risk: str | None = None,
    owner: str | None = None,
    business_unit: str | None = None,
    health_status: str | None = None,
    spend_min: float | None = None,
    spend_max: float | None = None,
    sort: str = "recent",
    stalled: bool = False,
) -> list[dict[str, Any]]:
    cards = [card(a, ctx) for a in ctx.apps]
    if stalled:
        cards = [c for c in cards if c["stalled_vs_median"]]
    if q:
        needle = q.lower()
        cards = [
            c
            for c in cards
            if needle in c["name"].lower()
            or needle in (c["owner"] or "").lower()
            or needle in c["business_problem"].lower()
        ]
    if stage and stage != "all":
        cards = [c for c in cards if c["stage"] == stage]
    if risk:
        cards = [c for c in cards if c["risk_tier"] == risk]
    if owner:
        cards = [c for c in cards if c["owner"] == owner]
    if business_unit:
        cards = [c for c in cards if c["business_unit"] == business_unit]
    if health_status:
        cards = [c for c in cards if c["health"] == health_status]
    if spend_min is not None:
        cards = [c for c in cards if c["monthly_spend_usd"].value >= spend_min]
    if spend_max is not None:
        cards = [c for c in cards if c["monthly_spend_usd"].value <= spend_max]
    keys = {
        "spend": lambda c: -(c["monthly_spend_usd"].value or 0),
        "value": lambda c: -(c["estimated_value_usd"].value or -1),
        "days": lambda c: -(c["days_in_stage"].value or 0),
        "recent": lambda c: c["last_activity_at"] or "",
        "name": lambda c: c["name"].lower(),
    }
    if sort == "recent":
        cards.sort(key=keys["recent"], reverse=True)
    else:
        cards.sort(key=keys.get(sort, keys["name"]))
    return cards


def portfolio(ctx: Context) -> dict[str, Any]:
    live = _live(ctx.apps)
    seed = (
        Provenance.FIXTURE
        if any(ctx.provenance(a) is Provenance.FIXTURE for a in live)
        else Provenance.MEASURED
    )
    cards = {a["app_id"]: card(a, ctx) for a in live}
    threshold = ctx.lc.raw["assist"]["threshold"]

    measured_month = sum(ctx.measured_spend.values())
    imported_month = sum(
        a.get("monthly_spend_micros") or 0 for a in live if a["app_id"] not in ctx.measured_spend
    )
    flagged = [c for c in cards.values() if c["assist_score"] >= threshold]
    var_value = sum(c["estimated_value_usd"].value or 0 for c in flagged)
    reason_counts: Counter[str] = Counter()
    for c in flagged:
        s = ctx.scores.get(c["app_id"], {})
        if s.get("reasons"):
            reason_counts[s["reasons"][0]["label"]] += 1
    scored_at = max((s["scored_at"] for s in ctx.scores.values()), default=None)

    stalled = [c for c in cards.values() if c["stalled_vs_median"]]
    approvals_waiting = sum(len(c["pending_gates"]) for c in cards.values())
    total_value = sum(c["estimated_value_usd"].value or 0 for c in cards.values())

    matrix: list[dict[str, Any]] = []
    tray: list[dict[str, Any]] = []
    for c in cards.values():
        v = c["estimated_value_usd"].value
        point = {
            "app_id": c["app_id"],
            "name": c["name"],
            "risk_tier": c["risk_tier"],
            "cost": c["monthly_spend_usd"].value,
            "value": v,
            "volume": next(
                (
                    a.get("monthly_volume") or a.get("active_users") or 0
                    for a in live
                    if a["app_id"] == c["app_id"]
                ),
                0,
            ),
            "stage": c["stage"],
        }
        (matrix if v is not None else tray).append(point)
    cost_mid = statistics.median([p["cost"] for p in matrix]) if matrix else 0
    value_mid = statistics.median([p["value"] for p in matrix]) if matrix else 0
    for p in matrix:
        high_value = p["value"] >= value_mid
        high_cost = p["cost"] > cost_mid
        p["quadrant"] = (
            ("Fix" if high_cost else "Scale")
            if high_value
            else ("Retire" if high_cost else "Watch")
        )

    attention = sorted(
        (c for c in cards.values() if c["assist_score"] > 0),
        key=lambda c: (-c["assist_score"], -(c["monthly_spend_usd"].value or 0)),
    )[:10]
    attention_rows = []
    for c in attention:
        reasons = ctx.scores.get(c["app_id"], {}).get("reasons", [])
        top = reasons[0] if reasons else {}
        attention_rows.append(
            {
                "app_id": c["app_id"],
                "name": c["name"],
                "stage": c["stage"],
                "score": c["assist_score"],
                "reason": top.get("label"),
                "evidence": top.get("evidence"),
                "action": top.get("action"),
            }
        )

    platforms = []
    for plat in ("abacus", "copilot", "custom", "managed"):
        group = [c for c in cards.values() if c["platform"] == plat]
        platforms.append(
            {
                "platform": plat,
                "apps": len(group),
                "spend": sum(c["monthly_spend_usd"].value or 0 for c in group),
            }
        )

    deadlines = [(c["next_gate"]["due_at"], c) for c in cards.values() if c["next_gate"]]
    nearest = min(deadlines, key=lambda d: d[0]) if deadlines else None

    src_apps = "apps (SYNTHETIC registry seed)"
    return {
        "generated_at": ctx.now.isoformat(),
        "filters": {"platform": ctx.filters.platform, "range_days": ctx.filters.range_days},
        "kpis": {
            "apps_in_production": metric(
                sum(c["stage"] == PRODUCTION for c in cards.values()), "apps", seed, src_apps
            ),
            "monthly_model_spend_usd": metric(
                measured_month / 1e6,
                "USD this month",
                Provenance.MEASURED,
                "artifacts/ledger_summary.json (settled attempts)",
            ),
            "imported_spend_usd": metric(
                imported_month / 1e6,
                "USD/month",
                seed,
                "apps.monthly_spend_micros (imported from external platforms)",
            ),
            "value_at_risk_usd": metric(
                var_value,
                "USD/month",
                Provenance.ASSUMPTION,
                "assist_scores >= 0.65 x business_case.monthly_value",
            ),
        },
        "assist": {
            "flagged_count": len(flagged),
            "top_reason": reason_counts.most_common(1)[0][0] if reason_counts else None,
            "scored_at": scored_at,
            "threshold": threshold,
        },
        "secondary": {
            "total_apps": metric(len(live), "apps", seed, src_apps),
            "stalled_apps": metric(len(stalled), "apps", seed, "time in stage > 1.5x stage median"),
            "estimated_monthly_value_usd": metric(
                total_value, "USD/month", Provenance.ASSUMPTION, "business_case"
            ),
            "open_incidents": metric(len(ctx.open_incident_apps), "incidents", seed, "incidents"),
            "approvals_waiting": metric(approvals_waiting, "gates", seed, "pending review gates"),
        },
        "matrix": {
            "points": matrix,
            "needs_business_case": tray,
            "cost_split": cost_mid,
            "value_split": value_mid,
            "provenance": {"cost": seed.value, "value": "ASSUMPTION"},
        },
        "attention": attention_rows,
        "platforms": platforms,
        "next_gate": None
        if nearest is None
        else {
            "app_id": nearest[1]["app_id"],
            "name": nearest[1]["name"],
            **nearest[1]["next_gate"],
        },
        "incident_open": bool(ctx.open_incident_apps),
    }


def spend_breakdown(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for a in _live(ctx.apps):
        spend, prov, src = ctx.spend_micros(a)
        if spend:
            rows.append(
                {
                    "app_id": a["app_id"],
                    "name": a["name"],
                    "platform": a["platform"],
                    "spend": metric(spend / 1e6, "USD/month", prov, src),
                }
            )
    return sorted(rows, key=lambda r: -r["spend"].value)


# Flow


def flow(ctx: Context) -> dict[str, Any]:
    end = ctx.now
    start = end - timedelta(days=ctx.filters.range_days)
    prior_start = start - timedelta(days=ctx.filters.range_days)

    def in_window(e: dict[str, Any], a: datetime, b: datetime) -> bool:
        t = _parse(e["created_at"])
        return t is not None and a <= t < b

    window = [e for e in ctx.app_events if in_window(e, start, end)]
    created = [e for e in window if e["kind"] == "created"]
    to_prod = [e for e in window if e["kind"] == "stage_change" and e["to_stage"] == PRODUCTION]
    published = [
        e
        for e in window
        if e["kind"] == "stage_change"
        and e["from_stage"] == "review_gates"
        and e["to_stage"] in ("evaluation", "monitored")
    ]
    rejected = [e for e in window if e["kind"] == "gate_reject"]

    first_created = {
        e["app_id"]: _parse(e["created_at"]) for e in ctx.app_events if e["kind"] == "created"
    }
    cycle = [
        ((_parse(e["created_at"]) - first_created[e["app_id"]]).total_seconds() / 86400)  # type: ignore[operator]
        for e in to_prod
        if e["app_id"] in first_created
    ]
    links: Counter[tuple[str, str]] = Counter(
        (e["from_stage"], e["to_stage"])
        for e in window
        if e["kind"] == "stage_change" and e["from_stage"]
    )

    def weekly(a: datetime, b: datetime) -> list[dict[str, Any]]:
        weeks = []
        t = a
        while t < b:
            u = min(b, t + timedelta(days=7))
            evs = [e for e in ctx.app_events if in_window(e, t, u)]
            weeks.append(
                {
                    "week_start": t.date().isoformat(),
                    "in": sum(e["kind"] == "created" for e in evs),
                    "out": sum(
                        e["kind"] == "stage_change" and e["to_stage"] == "retired" for e in evs
                    ),
                }
            )
            t = u
        return weeks

    durations = stage_durations(ctx.app_events)
    medians = [
        {"stage": s, "median_days": round(statistics.median(d), 1), "stays": len(d)}
        for s in ctx.lc.stages
        if (d := durations.get(s))
    ]

    owners: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"shipped": 0, "cycles": [], "spend": 0.0}
    )
    units: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"shipped": 0, "cycles": [], "spend": 0.0}
    )
    shipped_cycle: dict[str, float] = {}
    for e in ctx.app_events:
        shipped_at = _parse(e["created_at"])
        began = first_created.get(e["app_id"])
        if (
            e["kind"] == "stage_change"
            and e["to_stage"] == PRODUCTION
            and e["app_id"] not in shipped_cycle
            and shipped_at is not None
            and began is not None
        ):
            shipped_cycle[e["app_id"]] = (shipped_at - began).total_seconds() / 86400
    for a in ctx.apps:
        spend, _, _ = ctx.spend_micros(a)
        for key, table in ((a.get("owner") or "No owner", owners), (a["business_unit"], units)):
            row = table[key]
            row["spend"] += spend / 1e6
            if a["app_id"] in shipped_cycle:
                row["shipped"] += 1
                row["cycles"].append(shipped_cycle[a["app_id"]])

    def board(table: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows = [
            {
                "name": k,
                "shipped": v["shipped"],
                "median_cycle_days": round(statistics.median(v["cycles"]), 1)
                if v["cycles"]
                else None,
                "spend": round(v["spend"], 2),
            }
            for k, v in table.items()
        ]
        return sorted(rows, key=lambda r: (-r["shipped"], -r["spend"]))

    seed = Provenance.FIXTURE
    approvals = len(published) + len(rejected)
    return {
        "range_days": ctx.filters.range_days,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "header": {
            "apps_entered": metric(len(created), "apps", seed, "created events in range"),
            "apps_to_production": metric(len(to_prod), "apps", seed, "moves to monitored in range"),
            "median_days_to_production": metric(
                round(statistics.median(cycle), 1) if cycle else None,
                "days",
                seed,
                "created to first monitored, apps reaching production in range",
            ),
            "approval_rate": metric(
                round(len(published) / approvals, 3) if approvals else None,
                "ratio",
                seed,
                f"published / (published + rejected) in range; population {approvals}",
            ),
        },
        "approval_rate_detail": {"published": len(published), "rejected": len(rejected)},
        "sankey": [{"source": s, "target": t, "value": v} for (s, t), v in links.items()],
        "weekly": weekly(start, end),
        "weekly_prior": weekly(prior_start, start),
        "stage_medians": medians,
        "leaderboard": {"owners": board(owners), "business_units": board(units)},
        "data_source": "local event store (BigQuery export arrives in M6)",
        "last_export_at": None,
    }


# CSV export


def safe_cell(value: Any) -> str:
    """Neutralize spreadsheet formulas: prefix cells that start with formula characters."""
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


def catalog_csv(cards: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    header = [
        "app_id",
        "name",
        "owner",
        "business_unit",
        "platform",
        "stage",
        "risk_tier",
        "days_in_stage",
        "monthly_spend_usd",
        "spend_provenance",
        "estimated_value_usd",
        "health",
        "health_rule",
        "last_decision",
    ]
    writer.writerow(header)
    for c in cards:
        writer.writerow(
            [
                safe_cell(x)
                for x in [
                    c["app_id"],
                    c["name"],
                    c["owner"],
                    c["business_unit"],
                    c["platform"],
                    c["stage"],
                    c["risk_tier"],
                    c["days_in_stage"].value,
                    c["monthly_spend_usd"].value,
                    c["monthly_spend_usd"].provenance.value,
                    c["estimated_value_usd"].value,
                    c["health"],
                    c["health_rule"],
                    c["last_decision"],
                ]
            ]
        )
    return out.getvalue()
