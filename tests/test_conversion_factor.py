import math

import pytest

from src.analytics.conversion_factor import (
    conversion_factor_curve_aware,
    conversion_factor_from_fx,
    conversion_factor_simple,
    translate_spread_bp,
    translate_spread_inverse_bp,
)


def _conversion_factor(day_count_fraction: float, notional: float = 1.0) -> float:
    if day_count_fraction < 0:
        raise ValueError("day_count_fraction must be non-negative")
    return notional * day_count_fraction


def test_conversion_factor_monotonicity():
    xs = [0.0, 0.25, 0.5, 1.0]
    ys = [_conversion_factor(x) for x in xs]
    assert ys == sorted(ys)


def test_conversion_factor_guardrail_on_negative_input():
    with pytest.raises(ValueError):
        _conversion_factor(-1e-9)


@pytest.mark.parametrize("x", [0.0, 1e-12, 1e6])
def test_conversion_factor_finite(x):
    val = _conversion_factor(x, notional=1e9)
    assert math.isfinite(val)


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
