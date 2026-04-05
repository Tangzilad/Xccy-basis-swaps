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


def test_decomposition_identity_matches_synthetic_rate_function():
    foreign = 0.048
    basis = 0.012
    extra = 0.003

    out = all_in_funding_decomposition(0.065, foreign, basis, extra)
    synth = synthetic_domestic_funding_rate(foreign, basis, extra)
    assert math.isclose(out["synthetic_all_in"], synth)
