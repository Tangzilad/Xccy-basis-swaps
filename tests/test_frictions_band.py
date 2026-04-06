from __future__ import annotations

import pytest

from src.analytics.frictions import (
    deposit_adjusted_arbitrage_band_bp,
    friction_adjusted_arbitrage_band_bp,
)


def _base_args(raw_edge: float) -> dict[str, float]:
    return {
        "raw_basis_edge_bp": raw_edge,
        "capital_charge_bp": 8.0,
        "funding_spread_bp": 6.0,
        "cva_proxy_bp": 4.0,
        "fva_proxy_bp": 3.0,
        "clearing_friction_bp": 2.0,
        "liquidity_repo_friction_bp": 1.0,
    }


@pytest.mark.parametrize(
    "raw_edge,quality_mult,capacity_mult,expected_actionable",
    [
        (120.0, 1.0, 1.0, True),
        (18.0, 1.0, 1.0, False),
        (-130.0, 1.1, 1.2, True),
    ],
)
def test_arbitrage_band_actionability_under_parameter_sweeps(raw_edge, quality_mult, capacity_mult, expected_actionable):
    out = friction_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=raw_edge,
        capital_charge_bp=8.0,
        funding_spread_bp=6.0,
        cva_proxy_bp=4.0,
        fva_proxy_bp=3.0,
        clearing_friction_bp=2.0,
        liquidity_repo_friction_bp=1.0,
        counterparty_quality_multiplier=quality_mult,
        capacity_multiplier=capacity_mult,
    )

    assert out["upper_band_bp"] == -out["lower_band_bp"]
    assert out["is_actionable"] is expected_actionable
    if raw_edge >= 0:
        assert out["net_edge_bp"] <= raw_edge
    else:
        assert out["net_edge_bp"] >= raw_edge


def test_band_is_symmetric_for_positive_and_negative_raw_edges() -> None:
    pos = friction_adjusted_arbitrage_band_bp(**_base_args(35.0))
    neg = friction_adjusted_arbitrage_band_bp(**_base_args(-35.0))

    assert pos["upper_band_bp"] == pytest.approx(neg["upper_band_bp"])
    assert pos["lower_band_bp"] == pytest.approx(neg["lower_band_bp"])
    assert pos["upper_band_bp"] == pytest.approx(-pos["lower_band_bp"])


def test_actionability_threshold_equality_and_near_equality_behavior() -> None:
    equality = friction_adjusted_arbitrage_band_bp(**_base_args(24.0))
    just_over = friction_adjusted_arbitrage_band_bp(**_base_args(24.0001))
    just_under = friction_adjusted_arbitrage_band_bp(**_base_args(23.9999))

    assert equality["total_friction_bp"] == pytest.approx(24.0)
    assert equality["is_actionable"] is False
    assert just_under["is_actionable"] is False
    assert just_over["is_actionable"] is True


def test_deposit_adjusted_overlay_erodes_positive_apparent_edge() -> None:
    base = friction_adjusted_arbitrage_band_bp(**_base_args(33.0))
    adjusted = deposit_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=33.0,
        base_friction_bp=float(base["total_friction_bp"]),
        deposit_borrowing_bp=18.0,
        cva_bp=8.0,
        fva_bp=6.0,
        capital_charge_bp=5.0,
    )

    assert adjusted["total_friction_bp"] == pytest.approx(61.0)
    assert adjusted["net_edge_bp"] == pytest.approx(-28.0)
    assert adjusted["is_actionable"] is False


def test_deposit_adjusted_overlay_preserves_sign_convention_for_negative_raw_edge() -> None:
    adjusted = deposit_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=-40.0,
        base_friction_bp=10.0,
        deposit_borrowing_bp=5.0,
        cva_bp=3.0,
        fva_bp=2.0,
        capital_charge_bp=4.0,
    )

    # For negative raw edge, costs should push net edge toward zero by adding friction.
    assert adjusted["total_friction_bp"] == pytest.approx(24.0)
    assert adjusted["net_edge_bp"] == pytest.approx(-16.0)
    assert adjusted["is_actionable"] is True
