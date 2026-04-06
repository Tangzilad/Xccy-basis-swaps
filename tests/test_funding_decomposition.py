from __future__ import annotations

import math

from src.analytics.funding import (
    all_in_funding_decomposition,
    issuance_decision_from_spreads,
    synthetic_domestic_funding_rate,
)


def test_direct_vs_synthetic_funding_relationships():
    out = all_in_funding_decomposition(
        domestic_curve_rate=0.072,
        foreign_curve_rate=0.051,
        basis_spread=0.013,
        extra_spread=0.004,
    )

    assert math.isclose(out["domestic_all_in"], 0.076)
    assert math.isclose(out["synthetic_all_in"], 0.068)
    assert math.isclose(out["cross_market_gap"], out["synthetic_all_in"] - out["domestic_all_in"])


def test_decomposition_identities_for_domestic_and_foreign_synthetic_routes() -> None:
    domestic = 0.061
    foreign = 0.046
    basis = 0.012
    extra = 0.003

    out = all_in_funding_decomposition(domestic, foreign, basis, extra)

    assert math.isclose(out["domestic_all_in"], domestic + extra)
    assert math.isclose(out["synthetic_all_in"], foreign + basis + extra)
    assert math.isclose(out["synthetic_all_in"] - out["domestic_all_in"], (foreign + basis) - domestic)


def test_issuance_choice_gap_consistency() -> None:
    domestic, foreign, basis, extra = 0.064, 0.047, 0.006, 0.002

    out = all_in_funding_decomposition(domestic, foreign, basis, extra)
    issuance_gap = out["synthetic_all_in"] - out["domestic_all_in"]

    cheaper_route = "synthetic" if issuance_gap < 0 else "domestic"

    assert math.isclose(issuance_gap, out["cross_market_gap"])
    assert cheaper_route == "synthetic"


def test_decomposition_identity_matches_synthetic_rate_function():
    foreign = 0.048
    basis = 0.012
    extra = 0.003

    out = all_in_funding_decomposition(0.065, foreign, basis, extra)
    synth = synthetic_domestic_funding_rate(foreign, basis, extra)
    assert math.isclose(out["synthetic_all_in"], synth)


def test_cross_market_gap_and_directional_deltas_match_sign_conventions() -> None:
    domestic = 0.072
    foreign = 0.05
    extra = 0.002

    cheaper_synthetic = all_in_funding_decomposition(domestic, foreign, basis_spread=0.01, extra_spread=extra)
    expensive_synthetic = all_in_funding_decomposition(domestic, foreign, basis_spread=0.03, extra_spread=extra)

    assert cheaper_synthetic["cross_market_gap"] < 0
    assert cheaper_synthetic["synthetic_all_in"] < cheaper_synthetic["domestic_all_in"]

    assert expensive_synthetic["cross_market_gap"] > 0
    assert expensive_synthetic["synthetic_all_in"] > expensive_synthetic["domestic_all_in"]


def test_gap_identity_unaffected_by_equal_extra_spread_shift() -> None:
    domestic = 0.069
    foreign = 0.048
    basis = 0.009

    no_extra = all_in_funding_decomposition(domestic, foreign, basis, extra_spread=0.0)
    with_extra = all_in_funding_decomposition(domestic, foreign, basis, extra_spread=0.004)

    assert math.isclose(no_extra["cross_market_gap"], with_extra["cross_market_gap"], rel_tol=0.0, abs_tol=1e-12)


def test_worked_example_usd_recommendation_and_savings_magnitude() -> None:
    decision = issuance_decision_from_spreads(
        usd_spread_bp=200.0,
        huf_spread_bp=100.0,
        conversion_factor=1.091,
        basis_bp=39.5,
    )

    usd = decision["USD"]
    assert usd.preferred_route == "Issue HUF and swap into USD"
    assert usd.synthetic_spread_bp < usd.direct_spread_bp
    assert math.isclose(usd.synthetic_spread_bp, 148.6, rel_tol=0.0, abs_tol=1e-9)
    assert 50.0 < usd.savings_bp < 53.0


def test_worked_example_huf_reverse_rule_sign_and_magnitude() -> None:
    decision = issuance_decision_from_spreads(
        usd_spread_bp=200.0,
        huf_spread_bp=100.0,
        conversion_factor=1.091,
        basis_bp=39.5,
    )

    huf = decision["HUF"]
    assert huf.preferred_route == "Issue directly in HUF"
    assert huf.synthetic_spread_bp > huf.direct_spread_bp
    assert math.isclose(huf.synthetic_spread_bp, (200.0 - 39.5) / 1.091, rel_tol=0.0, abs_tol=1e-12)
    assert 45.0 < huf.savings_bp < 48.0


def test_deposit_vs_swap_gap_arithmetic_identity() -> None:
    """Deposit-vs-swap framing: synthetic minus direct equals basis-adjusted curve gap."""
    domestic = 0.058
    foreign = 0.041
    basis = 0.0095
    extra = 0.0015

    out = all_in_funding_decomposition(domestic, foreign, basis, extra)
    expected_gap = (foreign + basis + extra) - (domestic + extra)

    assert math.isclose(out["cross_market_gap"], expected_gap, rel_tol=0.0, abs_tol=1e-12)
