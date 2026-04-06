import math

import pytest

from src.analytics.conversion_factor import (
    conversion_factor_curve_aware,
    conversion_factor_from_fx,
    conversion_factor_simple,
    translate_spread_bp,
    translate_spread_inverse_bp,
)
from src.analytics.hedging import matched_vs_rolling_hedge_economics_bp
from src.analytics.parity import cip_theoretical_forward


def test_simple_vs_curve_aware_conversion_factor_invariant_under_cip_inputs():
    spot = 365.0
    usd_rate = 0.05
    huf_rate = 0.07
    t = 1.0

    forward = cip_theoretical_forward(spot, usd_rate, huf_rate, t)
    simple_factor = conversion_factor_from_fx(spot, forward)
    curve_aware_factor = (1.0 + huf_rate * t) / (1.0 + usd_rate * t)

    assert math.isclose(simple_factor, curve_aware_factor, rel_tol=0.0, abs_tol=1e-12)


def test_huf_usd_spread_round_trip_invariant() -> None:
    cf = conversion_factor_from_fx(spot_huf_per_usd=365.0, forward_huf_per_usd=371.0)
    huf_spread_bp = -42.0

    usd_spread_bp = translate_spread_bp(huf_spread_bp, cf)
    recovered_huf_spread_bp = translate_spread_inverse_bp(usd_spread_bp, cf)

    assert recovered_huf_spread_bp == pytest.approx(huf_spread_bp)


def test_conversion_factor_simple_payload_and_alias():
    payload = conversion_factor_simple(spot_huf_per_usd=360.0, forward_huf_per_usd=372.0)
    assert payload["method"] == "simple_ratio"
    assert payload["conversion_factor"] == pytest.approx(372.0 / 360.0)
    assert conversion_factor_from_fx(360.0, 372.0) == pytest.approx(payload["conversion_factor"])


def test_conversion_factor_curve_aware_payload_contains_components():
    payload = conversion_factor_curve_aware(
        spot_huf_per_usd=360.0,
        forward_huf_per_usd_by_tenor=[361.0, 363.0, 366.0],
        tenor_years=[0.5, 1.0, 2.0],
        discount_factors=[0.98, 0.95, 0.9],
        accrual_factors=[0.5, 0.5, 1.0],
    )
    assert payload["method"] == "curve_aware_annuity"
    assert payload["conversion_factor"] > 0
    assert len(payload["components"]["weights"]) == 3
    assert sum(payload["components"]["weights"]) == pytest.approx(1.0)


def test_conversion_factor_curve_aware_input_validation():
    with pytest.raises(ValueError):
        conversion_factor_curve_aware(
            spot_huf_per_usd=360.0,
            forward_huf_per_usd_by_tenor=[360.0, 361.0],
            tenor_years=[1.0],
            discount_factors=[0.99, 0.97],
        )

    with pytest.raises(ValueError):
        conversion_factor_curve_aware(
            spot_huf_per_usd=360.0,
            forward_huf_per_usd_by_tenor=[360.0],
            tenor_years=[1.0],
            discount_factors=[float("inf")],
        )


def test_translate_spread_with_payload_round_trip():
    payload = conversion_factor_simple(spot_huf_per_usd=360.0, forward_huf_per_usd=369.0)
    usd_spread = translate_spread_bp(25.0, payload)
    huf_spread = translate_spread_inverse_bp(usd_spread, payload)
    assert huf_spread == pytest.approx(25.0)


def test_matched_vs_rolling_stability_and_preferred_hedge_consistency() -> None:
    matched_cost = 64.0
    expected_rolling = 42.0
    roll_risk = 18.0
    risk_aversion = 1.0

    out = matched_vs_rolling_hedge_economics_bp(
        matched_hedge_cost_bp=matched_cost,
        expected_rolling_cost_bp=expected_rolling,
        roll_risk_proxy_bp=roll_risk,
        risk_aversion_multiplier=risk_aversion,
    )

    assert out["risk_adjusted_rolling_cost_bp"] == pytest.approx(expected_rolling + roll_risk)
    assert out["benefit_of_rolling_bp"] == pytest.approx(matched_cost - (expected_rolling + roll_risk))
    assert out["preferred_hedge"] == "rolling"

    tie = matched_vs_rolling_hedge_economics_bp(matched_cost, 50.0, 14.0, risk_aversion_multiplier=1.0)
    assert tie["benefit_of_rolling_bp"] == pytest.approx(0.0)
    assert tie["preferred_hedge"] == "matched"
