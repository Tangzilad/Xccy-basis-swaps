"""Funding decomposition utilities.

Canonical sign convention:
- Rates/spreads are decimals (100 bp = 0.01).
- Positive numbers increase all-in funding cost for the target currency.
- ``basis_spread`` is interpreted as the spread added when transforming
  foreign funding into domestic funding.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IssuanceChoice:
    """Comparison between direct issuance and swapped issuance."""

    currency: str
    direct_rate: float
    swapped_rate: float
    delta: float
    preferred_route: str
    savings_bp: float


def four_view_funding_decomposition(
    domestic_curve_rate: float,
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> dict[str, float]:
    """Compute four core all-in funding views and deltas.

    Views:
    - direct domestic
    - synthetic domestic via foreign + basis + extra
    - direct foreign
    - synthetic foreign via domestic - basis + extra
    """
    direct_domestic = domestic_curve_rate + extra_spread
    synthetic_domestic = foreign_curve_rate + basis_spread + extra_spread

    direct_foreign = foreign_curve_rate + extra_spread
    synthetic_foreign = domestic_curve_rate - basis_spread + extra_spread

    return {
        "domestic_curve": domestic_curve_rate,
        "foreign_curve": foreign_curve_rate,
        "basis": basis_spread,
        "extra_spread": extra_spread,
        "direct_domestic": direct_domestic,
        "synthetic_domestic": synthetic_domestic,
        "direct_foreign": direct_foreign,
        "synthetic_foreign": synthetic_foreign,
        "domestic_delta": synthetic_domestic - direct_domestic,
        "foreign_delta": synthetic_foreign - direct_foreign,
    }


def all_in_funding_decomposition(
    domestic_curve_rate: float,
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> dict[str, float]:
    """Backward-compatible domestic decomposition plus cross-market gap."""
    four_view = four_view_funding_decomposition(
        domestic_curve_rate=domestic_curve_rate,
        foreign_curve_rate=foreign_curve_rate,
        basis_spread=basis_spread,
        extra_spread=extra_spread,
    )
    return {
        **four_view,
        "domestic_all_in": four_view["direct_domestic"],
        "synthetic_all_in": four_view["synthetic_domestic"],
        "cross_market_gap": four_view["domestic_delta"],
    }


def synthetic_domestic_funding_rate(
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> float:
    """Compute domestic-equivalent funding from foreign funding plus basis."""
    return foreign_curve_rate + basis_spread + extra_spread


def synthetic_foreign_funding_rate(
    domestic_curve_rate: float,
    basis_spread: float,
    extra_spread: float = 0.0,
) -> float:
    """Compute foreign-equivalent funding from domestic funding plus reverse basis."""
    return domestic_curve_rate - basis_spread + extra_spread


def build_tenor_funding_table(
    *,
    domestic_label: str,
    foreign_label: str,
    domestic_curve_rate: float,
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float,
    tenors: tuple[str, ...],
    tenor_scales: tuple[float, ...],
    domestic_curve_slope: float = 0.0,
    foreign_curve_slope: float = 0.0,
) -> list[dict[str, float | str]]:
    """Create tenor-by-tenor table for both currencies from pure inputs."""
    rows: list[dict[str, float | str]] = []
    for tenor, scale in zip(tenors, tenor_scales, strict=True):
        views = four_view_funding_decomposition(
            domestic_curve_rate=domestic_curve_rate + domestic_curve_slope * scale,
            foreign_curve_rate=foreign_curve_rate + foreign_curve_slope * scale,
            basis_spread=basis_spread * scale,
            extra_spread=extra_spread,
        )
        rows.append(
            {
                "Tenor": tenor,
                f"{domestic_label} direct": views["direct_domestic"],
                f"{domestic_label} synthetic": views["synthetic_domestic"],
                f"{domestic_label} delta": views["domestic_delta"],
                f"{foreign_label} direct": views["direct_foreign"],
                f"{foreign_label} synthetic": views["synthetic_foreign"],
                f"{foreign_label} delta": views["foreign_delta"],
                "basis": views["basis"],
                "extra_spread": views["extra_spread"],
            }
        )
    return rows


def issuance_choice(
    *,
    issue_currency: str,
    direct_rate: float,
    swapped_rate: float,
) -> IssuanceChoice:
    """Return preferred issuance route and savings in bps."""
    delta = swapped_rate - direct_rate
    if delta < 0:
        preferred = f"Issue foreign and swap into {issue_currency}"
        savings = abs(delta) * 10_000.0
    else:
        preferred = f"Issue directly in {issue_currency}"
        savings = abs(delta) * 10_000.0
    return IssuanceChoice(
        currency=issue_currency,
        direct_rate=direct_rate,
        swapped_rate=swapped_rate,
        delta=delta,
        preferred_route=preferred,
        savings_bp=savings,
    )


def funding_role_interpretation(role: str) -> str:
    """Role-specific interpretation for funding transformation decisions."""
    role_map = {
        "issuer": "Prioritize the lowest all-in issuance route; monitor tenor pockets where synthetic funding saves spread.",
        "investor": "Treat persistent positive deltas as compensation for taking basis/funding-transfer risk and hedge slippage.",
        "treasury": "Balance issuance economics with liquidity, collateral capacity, and operational limits before executing basis-driven switches.",
    }
    return role_map.get(
        role,
        "Compare direct and synthetic curves, then validate execution constraints before acting on apparent spread advantages.",
    )


def funding_calculation_windows_payload(
    *,
    domestic_label: str,
    foreign_label: str,
    domestic_curve_rate: float,
    foreign_curve_rate: float,
    basis_spread: float,
    extra_spread: float,
) -> list[dict[str, str | tuple[str, ...]]]:
    """Build full calculation-window payload for the funding section."""
    views = four_view_funding_decomposition(
        domestic_curve_rate=domestic_curve_rate,
        foreign_curve_rate=foreign_curve_rate,
        basis_spread=basis_spread,
        extra_spread=extra_spread,
    )
    huf_choice = issuance_choice(
        issue_currency=domestic_label,
        direct_rate=views["direct_domestic"],
        swapped_rate=views["synthetic_domestic"],
    )
    usd_choice = issuance_choice(
        issue_currency=foreign_label,
        direct_rate=views["direct_foreign"],
        swapped_rate=views["synthetic_foreign"],
    )
    return [
        {
            "title": f"Direct {domestic_label} all-in",
            "formula": r"r_{dir,dom}=r_{domcurve}+s_{extra}",
            "substituted_values": f"$r_{{domcurve}}={domestic_curve_rate:.4%}, s_{{extra}}={extra_spread:.4%}$",
            "sign_notes": ("Positive spread adds to funding cost.",),
            "assumptions": ("Direct issuance ignores FX swap transformation.",),
            "result": f"{views['direct_domestic']:.4%}",
        },
        {
            "title": f"Synthetic {domestic_label} all-in",
            "formula": r"r_{syn,dom}=r_{forcurve}+b+s_{extra}",
            "substituted_values": f"$r_{{forcurve}}={foreign_curve_rate:.4%}, b={basis_spread:.4%}, s_{{extra}}={extra_spread:.4%}$",
            "sign_notes": ("Positive basis raises domestic synthetic cost.",),
            "assumptions": ("FX hedge is executed at quoted basis for the tenor.",),
            "result": f"{views['synthetic_domestic']:.4%}",
        },
        {
            "title": f"Direct {foreign_label} all-in",
            "formula": r"r_{dir,for}=r_{forcurve}+s_{extra}",
            "substituted_values": f"$r_{{forcurve}}={foreign_curve_rate:.4%}, s_{{extra}}={extra_spread:.4%}$",
            "sign_notes": ("Positive spread adds to funding cost.",),
            "assumptions": ("Foreign direct issuance has same issuer extra spread input.",),
            "result": f"{views['direct_foreign']:.4%}",
        },
        {
            "title": f"Synthetic {foreign_label} all-in",
            "formula": r"r_{syn,for}=r_{domcurve}-b+s_{extra}",
            "substituted_values": f"$r_{{domcurve}}={domestic_curve_rate:.4%}, b={basis_spread:.4%}, s_{{extra}}={extra_spread:.4%}$",
            "sign_notes": ("Domestic-to-foreign transfer uses reverse basis sign.",),
            "assumptions": ("Basis sign reverses when transforming in the opposite direction.",),
            "result": f"{views['synthetic_foreign']:.4%}",
        },
        {
            "title": f"{domestic_label} issuance choice",
            "formula": r"\Delta_{dom}=r_{syn,dom}-r_{dir,dom}",
            "substituted_values": f"${views['synthetic_domestic']:.6f}-{views['direct_domestic']:.6f}$",
            "sign_notes": ("Negative delta means swapped issuance is cheaper.",),
            "assumptions": ("Choice compares only all-in rate, not capacity constraints.",),
            "result": f"{huf_choice.preferred_route}; savings {huf_choice.savings_bp:.2f} bps",
        },
        {
            "title": f"{foreign_label} issuance choice",
            "formula": r"\Delta_{for}=r_{syn,for}-r_{dir,for}",
            "substituted_values": f"${views['synthetic_foreign']:.6f}-{views['direct_foreign']:.6f}$",
            "sign_notes": ("Negative delta means swapped issuance is cheaper.",),
            "assumptions": ("Choice compares only all-in rate, not liquidity constraints.",),
            "result": f"{usd_choice.preferred_route}; savings {usd_choice.savings_bp:.2f} bps",
        },
    ]
