"""Friction-adjusted arbitrage band logic.

Canonical sign convention:
- Inputs are in basis points.
- Positive raw edge means the trade appears profitable before frictions.
- Frictions are positive costs subtracted from raw edge.
"""

from __future__ import annotations


def total_friction_bp(
    capital_charge_bp: float,
    funding_spread_bp: float,
    cva_proxy_bp: float,
    fva_proxy_bp: float,
    clearing_friction_bp: float,
    liquidity_repo_friction_bp: float,
    counterparty_quality_multiplier: float = 1.0,
    capacity_multiplier: float = 1.0,
) -> float:
    """Aggregate friction stack with counterparty/capacity multipliers."""
    base = (
        capital_charge_bp
        + funding_spread_bp
        + cva_proxy_bp
        + fva_proxy_bp
        + clearing_friction_bp
        + liquidity_repo_friction_bp
    )
    return base * counterparty_quality_multiplier * capacity_multiplier


def friction_adjusted_arbitrage_band_bp(
    raw_basis_edge_bp: float,
    capital_charge_bp: float,
    funding_spread_bp: float,
    cva_proxy_bp: float,
    fva_proxy_bp: float,
    clearing_friction_bp: float,
    liquidity_repo_friction_bp: float,
    counterparty_quality_multiplier: float = 1.0,
    capacity_multiplier: float = 1.0,
) -> dict[str, float | bool]:
    """Return actionable band around zero after applying frictions."""
    friction = total_friction_bp(
        capital_charge_bp=capital_charge_bp,
        funding_spread_bp=funding_spread_bp,
        cva_proxy_bp=cva_proxy_bp,
        fva_proxy_bp=fva_proxy_bp,
        clearing_friction_bp=clearing_friction_bp,
        liquidity_repo_friction_bp=liquidity_repo_friction_bp,
        counterparty_quality_multiplier=counterparty_quality_multiplier,
        capacity_multiplier=capacity_multiplier,
    )
    net_edge = raw_basis_edge_bp - friction if raw_basis_edge_bp >= 0 else raw_basis_edge_bp + friction
    return {
        "raw_edge_bp": raw_basis_edge_bp,
        "total_friction_bp": friction,
        "upper_band_bp": friction,
        "lower_band_bp": -friction,
        "net_edge_bp": net_edge,
        "is_actionable": abs(raw_basis_edge_bp) > friction,
    }
