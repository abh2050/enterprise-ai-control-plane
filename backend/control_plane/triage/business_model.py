"""Net monthly value, breakeven precision, and sensitivity (Section 6.4).

Net monthly value = labor saved on correct auto routes
                  - misroute costs on wrong auto routes
                  - review labor
                  - model cost
                  - infrastructure.

Rates come from a scorecard (MEASURED). Model cost per case is MEASURED usage priced at
the paid-tier price card. Everything else is an ASSUMPTION from
configs/business_model.yaml, so every result is labeled ASSUMPTION.

Interpretation: an abstained case falls back to the manual process, so it adds no saving
and no cost. A reviewed case costs review minutes instead of manual minutes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from control_plane.triage.dataset import REPO_ROOT
from control_plane.triage.scorecard import Economics

BUSINESS_MODEL = REPO_ROOT / "configs" / "business_model.yaml"


@dataclass(frozen=True)
class Assumptions:
    monthly_volume: float
    manual_handling_minutes: float
    review_minutes: float
    loaded_labor_rate: float
    misroute_cost_standard: float
    misroute_cost_sensitive: float
    infrastructure_monthly: float

    @property
    def manual_cost_per_case(self) -> float:
        return self.manual_handling_minutes / 60 * self.loaded_labor_rate

    @property
    def review_cost_per_case(self) -> float:
        return self.review_minutes / 60 * self.loaded_labor_rate

    def economics(self) -> Economics:
        return Economics(
            review_cost_usd=self.review_cost_per_case,
            misroute_cost_standard_usd=self.misroute_cost_standard,
            misroute_cost_sensitive_usd=self.misroute_cost_sensitive,
        )


@dataclass(frozen=True)
class Rates:
    """Per-case rates from a scorecard on the frozen set (MEASURED)."""

    coverage: float  # share routed to auto
    auto_precision: float
    review_rate: float
    sensitive_share_of_wrong_autos: float
    model_cost_per_case_usd: float


def load_assumptions(path: Path = BUSINESS_MODEL) -> tuple[Assumptions, dict[str, Any]]:
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    values = {k: float(v["value"]) for k, v in raw["assumptions"].items()}
    for key, item in raw["assumptions"].items():
        if item.get("provenance") != "ASSUMPTION" or not item.get("justification"):
            raise ValueError(f"{key} must be labeled ASSUMPTION with a justification")
    return Assumptions(**values), raw


def _misroute_cost(a: Assumptions, sensitive_share: float) -> float:
    return (1 - sensitive_share) * a.misroute_cost_standard + (
        sensitive_share * a.misroute_cost_sensitive
    )


def net_monthly_value(a: Assumptions, r: Rates) -> dict[str, float]:
    v = a.monthly_volume
    correct_auto = v * r.coverage * r.auto_precision
    wrong_auto = v * r.coverage * (1 - r.auto_precision)
    labor_saved = correct_auto * a.manual_cost_per_case
    misroutes = wrong_auto * _misroute_cost(a, r.sensitive_share_of_wrong_autos)
    review = v * r.review_rate * a.review_cost_per_case
    model = v * r.model_cost_per_case_usd
    net = labor_saved - misroutes - review - model - a.infrastructure_monthly
    return {
        "labor_saved": labor_saved,
        "misroute_cost": misroutes,
        "review_labor": review,
        "model_cost": model,
        "infrastructure": a.infrastructure_monthly,
        "net_monthly_value": net,
    }


def breakeven_precision(a: Assumptions, r: Rates) -> float | None:
    """Auto precision below which automation loses money at this coverage.

    Solves V*c*p*S - V*c*(1-p)*M - fixed = 0 for p, where S is labor saved per correct
    auto route, M the blended misroute cost, and fixed the review, model, and
    infrastructure costs. Returns None when coverage is zero. A value above 1 means no
    precision breaks even.
    """
    if r.coverage <= 0:
        return None
    saved = a.manual_cost_per_case
    misroute = _misroute_cost(a, r.sensitive_share_of_wrong_autos)
    fixed = (
        a.monthly_volume * r.review_rate * a.review_cost_per_case
        + a.monthly_volume * r.model_cost_per_case_usd
        + a.infrastructure_monthly
    )
    return (fixed / (a.monthly_volume * r.coverage) + misroute) / (saved + misroute)


def sensitivity_table(
    a: Assumptions, r: Rates, misroute_costs: list[float], review_minutes: list[float]
) -> list[dict[str, float | None]]:
    rows = []
    for cost in misroute_costs:
        for minutes in review_minutes:
            varied = Assumptions(
                **{**a.__dict__, "misroute_cost_standard": cost, "review_minutes": minutes}
            )
            rows.append(
                {
                    "misroute_cost_standard": cost,
                    "review_minutes": minutes,
                    "net_monthly_value": net_monthly_value(varied, r)["net_monthly_value"],
                    "breakeven_precision": breakeven_precision(varied, r),
                }
            )
    return rows
