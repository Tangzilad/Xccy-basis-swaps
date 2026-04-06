from __future__ import annotations

import math

from src.analytics.funding import all_in_funding_decomposition, synthetic_domestic_funding_rate


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
