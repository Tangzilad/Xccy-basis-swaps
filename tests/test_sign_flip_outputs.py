from __future__ import annotations

import pytest

from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.funding import all_in_funding_decomposition
from src.analytics.xccy_swap import synthetic_funding_cost_outputs


def test_funding_cross_market_gap_flips_direction_with_basis_sign() -> None:
    common = dict(domestic_curve_rate=0.05, foreign_curve_rate=0.05, extra_spread=0.001)

    positive_basis = all_in_funding_decomposition(basis_spread=0.0025, **common)
    negative_basis = all_in_funding_decomposition(basis_spread=-0.0025, **common)

    assert positive_basis["cross_market_gap"] > 0
    assert negative_basis["cross_market_gap"] < 0


def test_synthetic_basis_drag_flips_sign_with_basis_sign() -> None:
    common = dict(
        spot_huf_per_usd=360.0,
        forward_huf_per_usd=365.0,
        huf_rate=0.065,
        year_fraction=1.0,
    )

    positive_basis = synthetic_funding_cost_outputs(basis_spread=0.0015, **common)
    negative_basis = synthetic_funding_cost_outputs(basis_spread=-0.0015, **common)

    assert positive_basis["basis_drag_bp"] > 0
    assert negative_basis["basis_drag_bp"] < 0
    assert positive_basis["basis_drag_bp"] == pytest.approx(-negative_basis["basis_drag_bp"])


def test_friction_adjusted_net_edge_changes_direction_with_raw_edge_sign() -> None:
    common = dict(
        capital_charge_bp=8.0,
        funding_spread_bp=6.0,
        cva_proxy_bp=4.0,
        fva_proxy_bp=3.0,
        clearing_friction_bp=2.0,
        liquidity_repo_friction_bp=1.0,
    )

    positive_raw = friction_adjusted_arbitrage_band_bp(raw_basis_edge_bp=50.0, **common)
    negative_raw = friction_adjusted_arbitrage_band_bp(raw_basis_edge_bp=-50.0, **common)

    assert positive_raw["net_edge_bp"] > 0
    assert negative_raw["net_edge_bp"] < 0
    assert positive_raw["sign_case"] == "positive_raw_edge"
    assert negative_raw["sign_case"] == "negative_raw_edge"
