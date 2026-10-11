import pytest

from control_plane.triage.business_model import (
    Assumptions,
    Rates,
    breakeven_precision,
    load_assumptions,
    net_monthly_value,
    sensitivity_table,
)

A = Assumptions(
    monthly_volume=1000,
    manual_handling_minutes=3,
    review_minutes=1,
    loaded_labor_rate=60,
    misroute_cost_standard=10,
    misroute_cost_sensitive=100,
    infrastructure_monthly=100,
)
R = Rates(
    coverage=0.5,
    auto_precision=0.9,
    review_rate=0.5,
    sensitive_share_of_wrong_autos=0.0,
    model_cost_per_case_usd=0.01,
)


def test_net_value_hand_computed() -> None:
    # correct autos 450 x $3 = 1350; wrong autos 50 x $10 = 500; review 500 x $1 = 500;
    # model 1000 x 0.01 = 10; infra 100 -> net 240
    out = net_monthly_value(A, R)
    assert out["labor_saved"] == pytest.approx(1350)
    assert out["misroute_cost"] == pytest.approx(500)
    assert out["review_labor"] == pytest.approx(500)
    assert out["net_monthly_value"] == pytest.approx(240)


def test_breakeven_gives_zero_net_value() -> None:
    p = breakeven_precision(A, R)
    assert p is not None
    at_breakeven = Rates(R.coverage, p, R.review_rate, 0.0, R.model_cost_per_case_usd)
    assert net_monthly_value(A, at_breakeven)["net_monthly_value"] == pytest.approx(0, abs=1e-9)
    # (610 / 500 + 10) / (3 + 10)
    assert p == pytest.approx((610 / 500 + 10) / 13)


def test_sensitive_misroutes_raise_breakeven() -> None:
    risky = Rates(R.coverage, R.auto_precision, R.review_rate, 0.2, R.model_cost_per_case_usd)
    assert breakeven_precision(A, risky) > breakeven_precision(A, R)  # type: ignore[operator]


def test_sensitivity_grid_and_config_labels() -> None:
    rows = sensitivity_table(A, R, [5, 10], [0.5, 1, 2])
    assert len(rows) == 6
    a, raw = load_assumptions()
    assert a.monthly_volume > 0
    assert all(v["provenance"] == "ASSUMPTION" for v in raw["assumptions"].values())
