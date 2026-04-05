"""Conversion-factor and spread translation utilities.

Canonical sign convention:
- Spreads are in bp.
- Conversion factor is multiplicative; >1 amplifies translated spread.
"""

from __future__ import annotations


def conversion_factor_from_fx(spot_huf_per_usd: float, forward_huf_per_usd: float) -> float:
    """FX conversion factor using forward/spot ratio."""
    return forward_huf_per_usd / spot_huf_per_usd


def translate_spread_bp(spread_bp: float, conversion_factor: float) -> float:
    """Translate spread by a conversion factor."""
    return spread_bp * conversion_factor


def translate_spread_inverse_bp(translated_spread_bp: float, conversion_factor: float) -> float:
    """Invert spread translation by conversion factor."""
    return translated_spread_bp / conversion_factor
