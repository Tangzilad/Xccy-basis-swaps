"""Funding decomposition utilities.

Canonical sign convention:
- Rates/spreads are decimals (100 bp = 0.01).
- Positive numbers increase all-in domestic funding cost.
"""

from __future__ import annotations


def all_in_funding_decomposition(
    domestic_curve_rate: float,
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> dict[str, float]:
    """Decompose all-in domestic funding cost from domestic/foreign views.

    - Direct domestic view: domestic curve + extra spread.
    - Synthetic foreign view: foreign curve + basis + extra spread.
    """
    domestic_all_in = domestic_curve_rate + extra_spread
    synthetic_all_in = foreign_curve_rate + basis_spread + extra_spread
    return {
        "domestic_curve": domestic_curve_rate,
        "foreign_curve": foreign_curve_rate,
        "basis": basis_spread,
        "extra_spread": extra_spread,
        "domestic_all_in": domestic_all_in,
        "synthetic_all_in": synthetic_all_in,
        "cross_market_gap": synthetic_all_in - domestic_all_in,
    }


def synthetic_domestic_funding_rate(
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> float:
    """Compute domestic-equivalent funding from foreign funding plus basis."""
    return foreign_curve_rate + basis_spread + extra_spread
