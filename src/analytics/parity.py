"""Covered Interest Parity (CIP) and basis utilities.

Canonical sign convention used across analytics modules:
- Rates/spreads are decimals (100 bp = 0.01).
- Spot/forward are quoted as HUF per 1 USD.
- Positive basis wedge means the observed forward implies a *higher* HUF rate
  than the input HUF curve (i.e., synthetic USD funding via HUF is richer/worse
  for a USD borrower).
"""

from __future__ import annotations


def cip_theoretical_forward(
    spot_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    year_fraction: float,
) -> float:
    """Return the no-basis CIP forward (HUF per USD).

    Formula: F = S * (1 + r_HUF * T) / (1 + r_USD * T)
    """
    return spot_huf_per_usd * (1.0 + huf_rate * year_fraction) / (1.0 + usd_rate * year_fraction)


def implied_huf_rate_from_spot_forward(
    spot_huf_per_usd: float,
    forward_huf_per_usd: float,
    usd_rate: float,
    year_fraction: float,
) -> float:
    """Infer HUF simple rate implied by (spot, forward, USD rate)."""
    return ((forward_huf_per_usd / spot_huf_per_usd) * (1.0 + usd_rate * year_fraction) - 1.0) / year_fraction


def implied_usd_rate_from_spot_forward(
    spot_huf_per_usd: float,
    forward_huf_per_usd: float,
    huf_rate: float,
    year_fraction: float,
) -> float:
    """Infer USD simple rate implied by (spot, forward, HUF rate)."""
    return ((1.0 + huf_rate * year_fraction) / (forward_huf_per_usd / spot_huf_per_usd) - 1.0) / year_fraction


def raw_basis_wedge_bp(
    spot_huf_per_usd: float,
    forward_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    year_fraction: float,
) -> float:
    """Return raw basis wedge in bp, as implied HUF - observed HUF curve."""
    implied_huf = implied_huf_rate_from_spot_forward(
        spot_huf_per_usd=spot_huf_per_usd,
        forward_huf_per_usd=forward_huf_per_usd,
        usd_rate=usd_rate,
        year_fraction=year_fraction,
    )
    return (implied_huf - huf_rate) * 10_000.0


def fair_value_comparison(
    spot_huf_per_usd: float,
    observed_forward_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    year_fraction: float,
) -> dict[str, float]:
    """Compare observed forward vs no-basis fair forward.

    Returns absolute and relative deviation plus basis wedge metrics.
    """
    fair_forward = cip_theoretical_forward(
        spot_huf_per_usd=spot_huf_per_usd,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )
    forward_diff = observed_forward_huf_per_usd - fair_forward
    rel_diff_bp = (forward_diff / fair_forward) * 10_000.0
    return {
        "observed_forward": observed_forward_huf_per_usd,
        "fair_forward_no_basis": fair_forward,
        "forward_difference": forward_diff,
        "forward_relative_bp": rel_diff_bp,
        "raw_basis_wedge_bp": raw_basis_wedge_bp(
            spot_huf_per_usd=spot_huf_per_usd,
            forward_huf_per_usd=observed_forward_huf_per_usd,
            usd_rate=usd_rate,
            huf_rate=huf_rate,
            year_fraction=year_fraction,
        ),
    }


def is_within_no_basis_band(
    spot_huf_per_usd: float,
    observed_forward_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    year_fraction: float,
    tolerance_bp: float = 1.0,
) -> bool:
    """True if observed forward is within a tolerance band around no-basis fair."""
    cmp = fair_value_comparison(
        spot_huf_per_usd=spot_huf_per_usd,
        observed_forward_huf_per_usd=observed_forward_huf_per_usd,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )
    return abs(cmp["forward_relative_bp"]) <= tolerance_bp
