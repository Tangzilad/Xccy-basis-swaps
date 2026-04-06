from __future__ import annotations

import math

from src.analytics.parity import (
    cip_theoretical_forward,
    fair_value_comparison,
    implied_huf_rate_from_spot_forward,
    implied_usd_rate_from_spot_forward,
    observed_forward_from_basis_spread,
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


def test_observed_forward_from_basis_preserves_wedge_sign_identity() -> None:
    spot = 372.0
    usd_rate = 0.051
    huf_rate = 0.073
    t = 1.0

    for basis in (-0.0012, 0.0, 0.0012):
        observed = observed_forward_from_basis_spread(spot, usd_rate, huf_rate, basis, t)
        wedge = raw_basis_wedge_bp(spot, observed, usd_rate, huf_rate, t)
        assert math.isclose(wedge, basis * 10_000.0, rel_tol=0.0, abs_tol=1e-10)


def test_forward_difference_and_raw_wedge_share_sign_convention() -> None:
    spot = 360.0
    usd_rate = 0.046
    huf_rate = 0.067
    t = 1.0
    fair = cip_theoretical_forward(spot, usd_rate, huf_rate, t)

    high = fair + 2.0
    low = fair - 2.0

    high_cmp = fair_value_comparison(spot, high, usd_rate, huf_rate, t)
    low_cmp = fair_value_comparison(spot, low, usd_rate, huf_rate, t)

    assert high_cmp["forward_difference"] > 0
    assert high_cmp["raw_basis_wedge_bp"] > 0
    assert low_cmp["forward_difference"] < 0
    assert low_cmp["raw_basis_wedge_bp"] < 0


def test_inversion_consistency_holds_for_non_1y_tenor() -> None:
    spot = 349.5
    usd_rate = 0.039
    huf_rate = 0.061
    t = 2.0

    forward = cip_theoretical_forward(spot, usd_rate, huf_rate, t)
    assert math.isclose(implied_huf_rate_from_spot_forward(spot, forward, usd_rate, t), huf_rate, abs_tol=1e-12)
    assert math.isclose(implied_usd_rate_from_spot_forward(spot, forward, huf_rate, t), usd_rate, abs_tol=1e-12)


def test_wedge_identity_equals_observed_minus_theoretical_forward() -> None:
    spot = 370.0
    usd_rate = 0.047
    huf_rate = 0.069
    t = 0.5
    observed = 376.25

    theoretical = cip_theoretical_forward(spot, usd_rate, huf_rate, t)
    comparison = fair_value_comparison(spot, observed, usd_rate, huf_rate, t)

    assert math.isclose(comparison["forward_difference"], observed - theoretical, rel_tol=0.0, abs_tol=1e-12)
