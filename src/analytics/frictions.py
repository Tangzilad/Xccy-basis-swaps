"""Friction-adjusted arbitrage band logic.

Canonical sign convention:
- Inputs are in basis points.
- Positive raw edge means the trade appears profitable before frictions.
- Negative raw edge means the mirror trade direction may be profitable.
- Frictions are positive costs and always shrink the absolute edge.
"""

from __future__ import annotations


def friction_components_bp(
    capital_charge_bp: float,
    funding_spread_bp: float,
    cva_proxy_bp: float,
    fva_proxy_bp: float,
    clearing_friction_bp: float,
    liquidity_repo_friction_bp: float,
) -> dict[str, float]:
    """Return the additive friction stack before multipliers."""
    return {
        "capital_charge_bp": capital_charge_bp,
        "funding_spread_bp": funding_spread_bp,
        "cva_proxy_bp": cva_proxy_bp,
        "fva_proxy_bp": fva_proxy_bp,
        "clearing_friction_bp": clearing_friction_bp,
        "liquidity_repo_friction_bp": liquidity_repo_friction_bp,
        "base_friction_bp": (
            capital_charge_bp
            + funding_spread_bp
            + cva_proxy_bp
            + fva_proxy_bp
            + clearing_friction_bp
            + liquidity_repo_friction_bp
        ),
    }


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
    components = friction_components_bp(
        capital_charge_bp=capital_charge_bp,
        funding_spread_bp=funding_spread_bp,
        cva_proxy_bp=cva_proxy_bp,
        fva_proxy_bp=fva_proxy_bp,
        clearing_friction_bp=clearing_friction_bp,
        liquidity_repo_friction_bp=liquidity_repo_friction_bp,
    )
    return (
        components["base_friction_bp"]
        * counterparty_quality_multiplier
        * capacity_multiplier
    )


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
) -> dict[str, float | bool | str]:
    """Return friction band and actionability for either edge sign.

    Sign handling:
    - raw > 0: net = raw - friction
    - raw < 0: net = raw + friction
    - raw = 0: net = 0

    A signal is actionable only when |raw| exceeds friction.
    """
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

    if raw_basis_edge_bp > 0:
        net_edge = raw_basis_edge_bp - friction
        sign_case = "positive_raw_edge"
    elif raw_basis_edge_bp < 0:
        net_edge = raw_basis_edge_bp + friction
        sign_case = "negative_raw_edge"
    else:
        net_edge = 0.0
        sign_case = "zero_raw_edge"

    return {
        "raw_edge_bp": raw_basis_edge_bp,
        "total_friction_bp": friction,
        "upper_band_bp": friction,
        "lower_band_bp": -friction,
        "net_edge_bp": net_edge,
        "is_actionable": abs(raw_basis_edge_bp) > friction,
        "sign_case": sign_case,
    }
