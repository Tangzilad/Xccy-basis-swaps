"""Hedging economics and pickup utilities.

Canonical sign convention:
- All spread-like inputs are in bp.
- Positive hedged pickup means economically better carry after hedge costs.
"""

from __future__ import annotations


def hedged_pickup_bp(
    gross_spread_pickup_bp: float,
    hedge_cost_bp: float,
    basis_drag_bp: float = 0.0,
    extra_friction_bp: float = 0.0,
) -> float:
    """Net pickup after hedge cost, basis drag, and extra frictions."""
    return gross_spread_pickup_bp - hedge_cost_bp - basis_drag_bp - extra_friction_bp


def roll_cost_and_risk_proxy_bp(
    current_roll_cost_bp: float,
    expected_roll_cost_bp: float,
    roll_volatility_bp: float,
    horizon_years: float,
) -> dict[str, float]:
    """Proxy roll-cost drift and roll-risk using sqrt-time scaling."""
    drift = expected_roll_cost_bp - current_roll_cost_bp
    roll_risk = roll_volatility_bp * (horizon_years**0.5)
    return {
        "expected_roll_drift_bp": drift,
        "roll_risk_proxy_bp": roll_risk,
    }


def matched_vs_rolling_hedge_economics_bp(
    matched_hedge_cost_bp: float,
    expected_rolling_cost_bp: float,
    roll_risk_proxy_bp: float,
    risk_aversion_multiplier: float = 1.0,
) -> dict[str, float | str]:
    """Compare matched-maturity hedge versus rolling hedge economics."""
    risk_adjusted_rolling_bp = expected_rolling_cost_bp + risk_aversion_multiplier * roll_risk_proxy_bp
    benefit_of_rolling_bp = matched_hedge_cost_bp - risk_adjusted_rolling_bp
    preferred = "rolling" if benefit_of_rolling_bp > 0 else "matched"
    return {
        "matched_cost_bp": matched_hedge_cost_bp,
        "risk_adjusted_rolling_cost_bp": risk_adjusted_rolling_bp,
        "benefit_of_rolling_bp": benefit_of_rolling_bp,
        "preferred_hedge": preferred,
    }
