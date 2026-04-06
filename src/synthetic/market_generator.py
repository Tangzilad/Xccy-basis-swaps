"""Synthetic cross-currency market generator.

This module provides a seed-reproducible API that emits stylized market objects for
HUF/USD basis modeling. It supports regime parameterization through level/slope/
curvature controls while applying validation and clipping guards to prevent
impossible outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

import numpy as np
import pandas as pd


# Conservative bounds used to keep generated markets economically coherent.
_DF_MIN = 1.0e-6
_DF_MAX = 1.0
_FORWARD_MIN = 120.0
_FORWARD_MAX = 1200.0
_BASIS_ABS_MAX_BPS = 800.0
_FRICTION_MIN_BPS = 0.0
_FRICTION_MAX_BPS = 1200.0
_CREDIT_MIN_BPS = 0.0
_CREDIT_MAX_BPS = 2000.0
_MAX_FORWARD_JUMP_PCT = 0.20
_MAX_RATE_GAP = 0.20


@dataclass(frozen=True)
class RegimeParams:
    """Regime controls for synthetic market generation.

    Attributes
    ----------
    name:
        Human readable regime label.
    level:
        Parallel move control. Positive values lift rates/spreads.
    slope:
        Front-vs-back end tilt control. Positive values steepen curves.
    curvature:
        Belly control. Positive values elevate intermediate maturities.
    noise_scale:
        Scale of idiosyncratic perturbations.
    """

    name: str = "baseline"
    level: float = 0.0
    slope: float = 0.0
    curvature: float = 0.0
    noise_scale: float = 1.0


def _as_regime_params(regime: str | Mapping[str, Any] | RegimeParams | None) -> RegimeParams:
    if regime is None:
        return RegimeParams()
    if isinstance(regime, RegimeParams):
        return regime
    if isinstance(regime, str):
        regime_key = regime.lower()
        if regime_key == "calm":
            return RegimeParams(name="calm", level=-0.25, slope=-0.10, curvature=-0.05, noise_scale=0.65)
        if regime_key == "stress":
            return RegimeParams(name="stress", level=0.60, slope=0.25, curvature=0.15, noise_scale=1.45)
        if regime_key in {"base", "baseline"}:
            return RegimeParams()
        raise ValueError(f"Unknown regime name: {regime!r}. Use 'calm', 'baseline', or 'stress'.")

    allowed = {"name", "level", "slope", "curvature", "noise_scale"}
    unknown = set(regime) - allowed
    if unknown:
        raise ValueError(f"Unknown regime parameter keys: {sorted(unknown)}")
    return RegimeParams(**regime)  # type: ignore[arg-type]


def _make_tenors(tenors: Sequence[str] | None = None) -> list[str]:
    if tenors is None:
        return ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]
    if not tenors:
        raise ValueError("tenors must not be empty")
    return list(tenors)


def _tenor_years(tenors: Sequence[str]) -> np.ndarray:
    years: list[float] = []
    for tenor in tenors:
        unit = tenor[-1].upper()
        value = float(tenor[:-1])
        if unit == "M":
            years.append(value / 12.0)
        elif unit == "Y":
            years.append(value)
        else:
            raise ValueError(f"Unsupported tenor unit in {tenor!r}; expected M or Y")
    out = np.asarray(years, dtype=float)
    if np.any(np.diff(out) <= 0):
        raise ValueError("tenors must be strictly increasing by maturity")
    return out


def _shape_function(x: np.ndarray, level: float, slope: float, curvature: float) -> np.ndarray:
    """Return additive curve control in decimal rate space."""

    # Normalize to [0, 1] maturity to make controls stable for custom tenor sets.
    z = (x - x.min()) / max(x.max() - x.min(), 1e-9)
    belly = 1.0 - ((z - 0.5) / 0.5) ** 2  # 0 at ends, 1 at center
    return (level * 0.005) + (slope * 0.004 * (z - 0.5)) + (curvature * 0.003 * belly)


def _clip_discount_factors(df: np.ndarray) -> np.ndarray:
    clipped = np.clip(df, _DF_MIN, _DF_MAX)
    # Enforce monotone non-increasing discount factors to avoid disconnected curves.
    for i in range(1, len(clipped)):
        if clipped[i] > clipped[i - 1]:
            clipped[i] = clipped[i - 1]
    return clipped


def _instantaneous_forwards(df: np.ndarray, t: np.ndarray) -> np.ndarray:
    logr = -np.log(df)
    dt = np.diff(t)
    return np.diff(logr) / np.maximum(dt, 1e-9)


def _repair_discount_curve(df: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Repair curve if jumps/negative forwards imply unrealistic structure."""

    safe_df = _clip_discount_factors(df)
    fwd = _instantaneous_forwards(safe_df, t)

    # Prevent absurd local forward spikes and negative rates beyond tolerance.
    fwd = np.clip(fwd, -0.015, 0.35)
    for i in range(1, len(fwd)):
        prior = max(abs(fwd[i - 1]), 1e-6)
        jump = (fwd[i] - fwd[i - 1]) / prior
        if jump > _MAX_FORWARD_JUMP_PCT:
            fwd[i] = fwd[i - 1] * (1.0 + _MAX_FORWARD_JUMP_PCT)
        elif jump < -_MAX_FORWARD_JUMP_PCT:
            fwd[i] = fwd[i - 1] * (1.0 - _MAX_FORWARD_JUMP_PCT)

    repaired = np.empty_like(safe_df)
    repaired[0] = safe_df[0]
    for i in range(1, len(safe_df)):
        dt = t[i] - t[i - 1]
        repaired[i] = repaired[i - 1] * np.exp(-fwd[i - 1] * dt)

    return _clip_discount_factors(repaired)


def _curve_df(tenors: Sequence[str], rates: np.ndarray, years: np.ndarray, label: str) -> pd.DataFrame:
    df = np.exp(-rates * years)
    df = _repair_discount_curve(df, years)
    zero_rates = -np.log(df) / np.maximum(years, 1e-9)
    return pd.DataFrame(
        {
            "tenor": list(tenors),
            "years": years,
            f"{label}_zero_rate": zero_rates,
            "discount_factor": df,
        }
    )


def generate_market(
    seed: int | None = None,
    regime: str | Mapping[str, Any] | RegimeParams | None = None,
    tenors: Sequence[str] | None = None,
    spot_fx: float = 365.0,
) -> Dict[str, Any]:
    """Generate a synthetic HUF/USD market snapshot.

    Returns the exact payload requested by downstream consumers:
    tenors, huf_curve_df, usd_curve_df, spot_fx, market_forward_df,
    theoretical_forward_df, basis_curve_df, credit_assumptions,
    friction_assumptions, regime_summary.
    """

    reg = _as_regime_params(regime)
    tenor_list = _make_tenors(tenors)
    years = _tenor_years(tenor_list)

    rng = np.random.default_rng(seed)
    regime_shape = _shape_function(years, reg.level, reg.slope, reg.curvature)

    base_usd = 0.035 + 0.004 * np.log1p(years)
    base_huf = 0.065 + 0.006 * np.log1p(years)

    usd_noise = rng.normal(0.0, 0.0007 * reg.noise_scale, len(years))
    huf_noise = rng.normal(0.0, 0.0010 * reg.noise_scale, len(years))

    usd_rates = np.clip(base_usd + 0.65 * regime_shape + usd_noise, -0.005, 0.18)
    huf_rates = np.clip(base_huf + 1.00 * regime_shape + huf_noise, 0.005, 0.30)

    # Enforce stylized economics: HUF generally above USD by a positive wedge.
    min_wedge = 0.006
    huf_rates = np.maximum(huf_rates, usd_rates + min_wedge)
    huf_rates = np.minimum(huf_rates, usd_rates + _MAX_RATE_GAP)

    usd_curve_df = _curve_df(tenor_list, usd_rates, years, "usd")
    huf_curve_df = _curve_df(tenor_list, huf_rates, years, "huf")

    usd_df = usd_curve_df["discount_factor"].to_numpy()
    huf_df = huf_curve_df["discount_factor"].to_numpy()

    theoretical_forward = spot_fx * usd_df / np.maximum(huf_df, _DF_MIN)
    theoretical_forward = np.clip(theoretical_forward, _FORWARD_MIN, _FORWARD_MAX)

    # Calm regimes compress basis/frictions; stress widens them.
    stress_score = np.clip(reg.level + 0.5 * reg.slope + 0.25 * reg.curvature, -1.0, 1.5)
    basis_base_bps = 22.0 + 50.0 * stress_score
    credit_base_bps = 35.0 + 95.0 * max(stress_score, -0.2)
    friction_base_bps = 14.0 + 80.0 * max(stress_score, -0.25)

    basis_bps = basis_base_bps + np.linspace(-4.0, 7.0, len(years))
    basis_bps += rng.normal(0.0, 3.0 * reg.noise_scale, len(years))
    basis_bps = np.clip(basis_bps, -_BASIS_ABS_MAX_BPS, _BASIS_ABS_MAX_BPS)

    credit_bps = np.clip(
        credit_base_bps + np.linspace(4.0, -3.0, len(years)) + rng.normal(0.0, 4.0, len(years)),
        _CREDIT_MIN_BPS,
        _CREDIT_MAX_BPS,
    )
    friction_bps = np.clip(
        friction_base_bps + np.linspace(2.0, 6.0, len(years)) + rng.normal(0.0, 3.0, len(years)),
        _FRICTION_MIN_BPS,
        _FRICTION_MAX_BPS,
    )

    wedge = (basis_bps + credit_bps + friction_bps) / 1.0e4
    market_forward = theoretical_forward * np.exp(wedge * years)

    # Guard against absurd term structures in forwards (disconnected jumps).
    market_forward = np.clip(market_forward, _FORWARD_MIN, _FORWARD_MAX)
    for i in range(1, len(market_forward)):
        max_step = market_forward[i - 1] * (1.0 + _MAX_FORWARD_JUMP_PCT)
        min_step = market_forward[i - 1] * (1.0 - _MAX_FORWARD_JUMP_PCT)
        market_forward[i] = float(np.clip(market_forward[i], min_step, max_step))

    theoretical_forward_df = pd.DataFrame(
        {"tenor": tenor_list, "years": years, "theoretical_forward": theoretical_forward}
    )
    market_forward_df = pd.DataFrame({"tenor": tenor_list, "years": years, "market_forward": market_forward})
    basis_curve_df = pd.DataFrame(
        {
            "tenor": tenor_list,
            "years": years,
            "basis_bps": basis_bps,
            "implied_basis_decimal": basis_bps / 1.0e4,
        }
    )

    credit_assumptions = pd.DataFrame(
        {
            "tenor": tenor_list,
            "years": years,
            "credit_spread_bps": credit_bps,
            "credit_spread_decimal": credit_bps / 1.0e4,
        }
    )
    friction_assumptions = pd.DataFrame(
        {
            "tenor": tenor_list,
            "years": years,
            "funding_friction_bps": friction_bps,
            "funding_friction_decimal": friction_bps / 1.0e4,
        }
    )

    regime_summary = {
        "name": reg.name,
        "level": reg.level,
        "slope": reg.slope,
        "curvature": reg.curvature,
        "noise_scale": reg.noise_scale,
        "stress_score": float(stress_score),
        "stylized_economics": {
            "baseline_huf_above_usd": True,
            "calm_compresses_wedge": stress_score < 0,
            "stress_widens_wedge": stress_score > 0,
        },
    }

    return {
        "tenors": tenor_list,
        "huf_curve_df": huf_curve_df,
        "usd_curve_df": usd_curve_df,
        "spot_fx": float(np.clip(spot_fx, _FORWARD_MIN, _FORWARD_MAX)),
        "market_forward_df": market_forward_df,
        "theoretical_forward_df": theoretical_forward_df,
        "basis_curve_df": basis_curve_df,
        "credit_assumptions": credit_assumptions,
        "friction_assumptions": friction_assumptions,
        "regime_summary": regime_summary,
    }


__all__ = ["RegimeParams", "generate_market"]
