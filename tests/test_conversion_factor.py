from __future__ import annotations

import math

from src.analytics.conversion_factor import (
    conversion_factor_from_fx,
    translate_spread_bp,
    translate_spread_inverse_bp,
)
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


def test_conversion_translation_round_trip_invariant():
    cf = conversion_factor_from_fx(spot_huf_per_usd=365.0, forward_huf_per_usd=371.0)
    original = -42.0
    translated = translate_spread_bp(original, cf)
    recovered = translate_spread_inverse_bp(translated, cf)

    assert math.isclose(original, recovered, rel_tol=0.0, abs_tol=1e-12)
