"""Covered Interest Parity (CIP) and basis utilities.

Canonical sign convention used across analytics modules:
- Rates/spreads are decimals (100 bp = 0.01).
- Spot/forward are quoted as HUF per 1 USD.
- Positive basis wedge means the observed forward implies a *higher* HUF rate
  than the input HUF curve (i.e., synthetic USD funding via HUF is richer/worse
  for a USD borrower).
"""

from __future__ import annotations


def tenor_to_year_fraction(tenor_label: str) -> float:
    """Convert tenor labels like 3M/1Y to year fractions."""
    unit = tenor_label[-1].upper()
    value = float(tenor_label[:-1])
    if unit == "M":
        return value / 12.0
    if unit == "Y":
        return value
    raise ValueError(f"Unsupported tenor label: {tenor_label!r}")


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


def observed_forward_from_basis_spread(
    spot_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    basis_spread: float,
    year_fraction: float,
) -> float:
    """Build an observed forward from a HUF-side basis spread in decimal terms."""
    return spot_huf_per_usd * (1.0 + (huf_rate + basis_spread) * year_fraction) / (1.0 + usd_rate * year_fraction)


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


def parity_decomposition(
    spot_huf_per_usd: float,
    observed_forward_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    year_fraction: float,
) -> dict[str, float]:
    """Return a structured parity decomposition payload for one tenor."""
    cip_forward = cip_theoretical_forward(
        spot_huf_per_usd=spot_huf_per_usd,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )
    implied_huf = implied_huf_rate_from_spot_forward(
        spot_huf_per_usd=spot_huf_per_usd,
        forward_huf_per_usd=observed_forward_huf_per_usd,
        usd_rate=usd_rate,
        year_fraction=year_fraction,
    )
    implied_usd = implied_usd_rate_from_spot_forward(
        spot_huf_per_usd=spot_huf_per_usd,
        forward_huf_per_usd=observed_forward_huf_per_usd,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )
    forward_diff = observed_forward_huf_per_usd - cip_forward
    relative_bp = (forward_diff / cip_forward) * 10_000.0
    wedge_bp = (implied_huf - huf_rate) * 10_000.0
    return {
        "spot": spot_huf_per_usd,
        "year_fraction": year_fraction,
        "observed_forward": observed_forward_huf_per_usd,
        "cip_implied_forward": cip_forward,
        "implied_huf_rate": implied_huf,
        "implied_usd_rate": implied_usd,
        "forward_difference": forward_diff,
        "forward_relative_bp": relative_bp,
        "raw_basis_wedge_bp": wedge_bp,
        "basis_spread": implied_huf - huf_rate,
    }


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
    result = parity_decomposition(
        spot_huf_per_usd=spot_huf_per_usd,
        observed_forward_huf_per_usd=observed_forward_huf_per_usd,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )
    return {
        "observed_forward": result["observed_forward"],
        "fair_forward_no_basis": result["cip_implied_forward"],
        "forward_difference": result["forward_difference"],
        "forward_relative_bp": result["forward_relative_bp"],
        "raw_basis_wedge_bp": result["raw_basis_wedge_bp"],
    }


def tenor_ladder_decomposition(
    spot_huf_per_usd: float,
    usd_rate: float,
    huf_rate: float,
    tenor_labels: list[str],
    anchor_observed_forward: float,
    anchor_tenor_label: str,
) -> list[dict[str, float | str]]:
    """Build tenor ladder payload using anchor implied basis spread across tenors."""
    anchor_years = tenor_to_year_fraction(anchor_tenor_label)
    anchor = parity_decomposition(
        spot_huf_per_usd=spot_huf_per_usd,
        observed_forward_huf_per_usd=anchor_observed_forward,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=anchor_years,
    )
    basis_spread = float(anchor["basis_spread"])

    ladder: list[dict[str, float | str]] = []
    for tenor in tenor_labels:
        years = tenor_to_year_fraction(tenor)
        observed_forward = observed_forward_from_basis_spread(
            spot_huf_per_usd=spot_huf_per_usd,
            usd_rate=usd_rate,
            huf_rate=huf_rate,
            basis_spread=basis_spread,
            year_fraction=years,
        )
        row = parity_decomposition(
            spot_huf_per_usd=spot_huf_per_usd,
            observed_forward_huf_per_usd=observed_forward,
            usd_rate=usd_rate,
            huf_rate=huf_rate,
            year_fraction=years,
        )
        ladder.append({"tenor": tenor, **row})
    return ladder


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
