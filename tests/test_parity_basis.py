from __future__ import annotations

import math

from src.analytics.parity import (
    cip_theoretical_forward,
    implied_huf_rate_from_spot_forward,
    implied_usd_rate_from_spot_forward,
    raw_basis_wedge_bp,
)


def test_parity_theoretical_forward_and_implied_rates_are_consistent():
    spot = 365.0
    usd_rate = 0.052
    huf_rate = 0.074
    t = 1.5

    fwd = cip_theoretical_forward(spot, usd_rate, huf_rate, t)
    implied_huf = implied_huf_rate_from_spot_forward(spot, fwd, usd_rate, t)
    implied_usd = implied_usd_rate_from_spot_forward(spot, fwd, huf_rate, t)

    assert math.isclose(implied_huf, huf_rate, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(implied_usd, usd_rate, rel_tol=0.0, abs_tol=1e-12)


def test_raw_basis_wedge_sign_checks_follow_convention():
    spot = 365.0
    usd_rate = 0.05
    huf_rate = 0.07
    t = 1.0

    fair_fwd = cip_theoretical_forward(spot, usd_rate, huf_rate, t)
    wedge_positive = raw_basis_wedge_bp(spot, fair_fwd * 1.01, usd_rate, huf_rate, t)
    wedge_negative = raw_basis_wedge_bp(spot, fair_fwd * 0.99, usd_rate, huf_rate, t)

    assert wedge_positive > 0
    assert wedge_negative < 0
