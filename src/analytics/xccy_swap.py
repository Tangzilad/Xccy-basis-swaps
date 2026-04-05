"""Cross-currency swap cashflow and basis-leg utilities.

Canonical sign convention:
- Perspective is the USD-floating receiver / HUF-floating payer.
- Positive cashflow values are amounts received by that perspective.
- Rates/spreads are decimals (100 bp = 0.01); basis is added to HUF coupons.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SwapPeriod:
    """Single coupon period definition."""

    end_date: str
    accrual_year_fraction: float
    usd_float_rate: float
    huf_float_rate: float


def floating_coupon_stream(notional: float, rates: Iterable[float], accruals: Iterable[float]) -> list[float]:
    """Compute floating coupon cashflows as notional * rate * accrual."""
    return [notional * r * a for r, a in zip(rates, accruals, strict=True)]


def basis_adjusted_coupon_leg(
    huf_notional: float,
    huf_float_rates: Iterable[float],
    accruals: Iterable[float],
    basis_spread: float,
) -> list[float]:
    """Compute HUF leg coupons with basis spread added to reference rate."""
    return [huf_notional * (r + basis_spread) * a for r, a in zip(huf_float_rates, accruals, strict=True)]


def cashflow_timeline(
    usd_notional: float,
    spot_huf_per_usd: float,
    periods: Iterable[SwapPeriod],
    basis_spread: float = 0.0,
    include_principal_exchange: bool = True,
) -> list[dict[str, float | str]]:
    """Build swap timeline including principal exchanges and coupon streams."""
    huf_notional = usd_notional * spot_huf_per_usd
    timeline: list[dict[str, float | str]] = []

    if include_principal_exchange:
        timeline.append(
            {
                "date": "start",
                "usd_cashflow": -usd_notional,
                "huf_cashflow": huf_notional,
                "net_usd_equiv_at_spot": -usd_notional + huf_notional / spot_huf_per_usd,
            }
        )

    periods_list = list(periods)
    for p in periods_list:
        usd_coupon = usd_notional * p.usd_float_rate * p.accrual_year_fraction
        huf_coupon = huf_notional * (p.huf_float_rate + basis_spread) * p.accrual_year_fraction
        timeline.append(
            {
                "date": p.end_date,
                "usd_cashflow": usd_coupon,
                "huf_cashflow": -huf_coupon,
                "net_usd_equiv_at_spot": usd_coupon - huf_coupon / spot_huf_per_usd,
            }
        )

    if include_principal_exchange:
        end_date = periods_list[-1].end_date if periods_list else "end"
        timeline.append(
            {
                "date": end_date,
                "usd_cashflow": usd_notional,
                "huf_cashflow": -huf_notional,
                "net_usd_equiv_at_spot": usd_notional - huf_notional / spot_huf_per_usd,
            }
        )

    return timeline


def synthetic_funding_cost_outputs(
    spot_huf_per_usd: float,
    forward_huf_per_usd: float,
    huf_rate: float,
    basis_spread: float,
    year_fraction: float,
) -> dict[str, float]:
    """Return synthetic USD funding metrics from HUF funding plus basis.

    Uses simple-rate approximation.
    """
    no_basis_implied_usd = ((1.0 + huf_rate * year_fraction) / (forward_huf_per_usd / spot_huf_per_usd) - 1.0) / year_fraction
    basis_adjusted_implied_usd = (
        (1.0 + (huf_rate + basis_spread) * year_fraction) / (forward_huf_per_usd / spot_huf_per_usd) - 1.0
    ) / year_fraction
    return {
        "synthetic_usd_rate_no_basis": no_basis_implied_usd,
        "synthetic_usd_rate_with_basis": basis_adjusted_implied_usd,
        "basis_drag_bp": (basis_adjusted_implied_usd - no_basis_implied_usd) * 10_000.0,
    }
