import pytest

from src.analytics.hedging import matched_vs_rolling_hedge_economics_bp


def test_hedge_method_preference_flips_when_roll_risk_rises() -> None:
    common_kwargs = {
        "matched_hedge_cost_bp": 55.0,
        "expected_rolling_cost_bp": 38.0,
        "risk_aversion_multiplier": 1.0,
    }

    low_risk = matched_vs_rolling_hedge_economics_bp(roll_risk_proxy_bp=8.0, **common_kwargs)
    high_risk = matched_vs_rolling_hedge_economics_bp(roll_risk_proxy_bp=24.0, **common_kwargs)

    assert low_risk["preferred_hedge"] == "rolling"
    assert high_risk["preferred_hedge"] == "matched"
    assert low_risk["risk_adjusted_rolling_cost_bp"] == pytest.approx(46.0)
    assert high_risk["risk_adjusted_rolling_cost_bp"] == pytest.approx(62.0)


def test_rolling_benefit_declines_monotonically_with_roll_risk() -> None:
    base = matched_vs_rolling_hedge_economics_bp(60.0, 40.0, 5.0, risk_aversion_multiplier=0.8)
    stressed = matched_vs_rolling_hedge_economics_bp(60.0, 40.0, 25.0, risk_aversion_multiplier=0.8)

    assert stressed["benefit_of_rolling_bp"] < base["benefit_of_rolling_bp"]
