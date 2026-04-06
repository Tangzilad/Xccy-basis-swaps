from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from src.scenarios.scenario_library import (
    SCENARIO_LIBRARY,
    Scenario,
    apply_scenario,
    custom_flattener,
    custom_parallel,
    custom_steepener,
)
from src.synthetic.market_generator import generate_market

_LEVEL_RANGE = (-2.0, 2.0)
_SLOPE_RANGE = (-2.0, 2.0)
_CURVATURE_RANGE = (-2.0, 2.0)
_NOISE_RANGE = (0.2, 3.0)
_SPOT_RANGE = (120.0, 1200.0)
_BASIS_RANGE_BPS = (-800.0, 800.0)
_FRICTION_RANGE_BPS = (0.0, 1200.0)
_CREDIT_RANGE_BPS = (0.0, 2000.0)
_FORWARD_RANGE = (120.0, 1200.0)


@dataclass(frozen=True)
class ScenarioDelta:
    level: float = 0.0
    slope: float = 0.0
    curvature: float = 0.0
    spot_shift: float = 0.0
    basis_shift_bps: float = 0.0
    credit_shift_bps: float = 0.0
    friction_shift_bps: float = 0.0
    liquidity_shift: float = 0.0


_DEFAULT_REGIME = {
    "name": "baseline",
    "level": 0.0,
    "slope": 0.0,
    "curvature": 0.0,
    "noise_scale": 1.0,
}


def clip_regime(regime: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(regime.get("name", "baseline")),
        "level": float(np.clip(float(regime.get("level", 0.0)), *_LEVEL_RANGE)),
        "slope": float(np.clip(float(regime.get("slope", 0.0)), *_SLOPE_RANGE)),
        "curvature": float(np.clip(float(regime.get("curvature", 0.0)), *_CURVATURE_RANGE)),
        "noise_scale": float(np.clip(float(regime.get("noise_scale", 1.0)), *_NOISE_RANGE)),
    }


def _default_market_state(seed: int = 7) -> dict[str, Any]:
    regime = clip_regime(_DEFAULT_REGIME)
    base_snapshot = generate_market(seed=seed, regime=regime)
    return {
        "seed": int(seed),
        "regime": regime,
        "base_snapshot": base_snapshot,
        "stressed_snapshot": deepcopy(base_snapshot),
        "scenario": "none",
    }


def ensure_market_state(state: Mapping[str, Any] | None, *, seed: int = 7) -> dict[str, Any]:
    if not state:
        return _default_market_state(seed=seed)
    out = deepcopy(dict(state))
    out["seed"] = int(out.get("seed", seed))
    out["regime"] = clip_regime(out.get("regime", _DEFAULT_REGIME))
    if "base_snapshot" not in out:
        out["base_snapshot"] = generate_market(seed=out["seed"], regime=out["regime"])
    if "stressed_snapshot" not in out:
        out["stressed_snapshot"] = deepcopy(out["base_snapshot"])
    out.setdefault("scenario", "none")
    return out


def regenerate_market_state(state: Mapping[str, Any]) -> dict[str, Any]:
    st = ensure_market_state(state)
    st["base_snapshot"] = generate_market(seed=st["seed"], regime=st["regime"])
    st["stressed_snapshot"] = deepcopy(st["base_snapshot"])
    st["scenario"] = "none"
    return st


def _bucket_to_shape_shift(bucket: Mapping[str, float]) -> tuple[float, float, float]:
    front = float(bucket.get("front", 0.0))
    belly = float(bucket.get("belly", 0.0))
    back = float(bucket.get("back", 0.0))
    level = (front + belly + back) / 3.0
    slope = back - front
    curvature = belly - 0.5 * (front + back)
    return level, slope, curvature


def _scenario_to_delta(shocked: Mapping[str, Any]) -> ScenarioDelta:
    huf_level, huf_slope, huf_curve = _bucket_to_shape_shift(shocked.get("huf_rates", {}))
    usd_level, usd_slope, usd_curve = _bucket_to_shape_shift(shocked.get("usd_rates", {}))
    basis_level, _, _ = _bucket_to_shape_shift(shocked.get("basis_curve", {}))
    rate_level = 0.6 * huf_level + 0.4 * usd_level
    rate_slope = 0.6 * huf_slope + 0.4 * usd_slope
    rate_curve = 0.6 * huf_curve + 0.4 * usd_curve

    credit = shocked.get("credit_spreads", {})
    funding = shocked.get("funding_spreads", {})
    credit_shift = 0.5 * (float(credit.get("sovereign", 0.0)) + float(credit.get("banks", 0.0)))
    friction_shift = 0.5 * (float(funding.get("secured", 0.0)) + float(funding.get("unsecured", 0.0)))

    return ScenarioDelta(
        level=rate_level / 0.5,
        slope=rate_slope,
        curvature=rate_curve / 0.5,
        spot_shift=float(shocked.get("spot", 0.0)),
        basis_shift_bps=basis_level,
        credit_shift_bps=credit_shift,
        friction_shift_bps=friction_shift,
        liquidity_shift=float(shocked.get("liquidity_repo_availability", 0.0)) / 100.0,
    )


def _recompute_forwards(snapshot: dict[str, Any]) -> None:
    years = snapshot["basis_curve_df"]["years"].to_numpy(dtype=float)
    basis = snapshot["basis_curve_df"]["basis_bps"].to_numpy(dtype=float)
    credit = snapshot["credit_assumptions"]["credit_spread_bps"].to_numpy(dtype=float)
    fric = snapshot["friction_assumptions"]["funding_friction_bps"].to_numpy(dtype=float)
    theo = snapshot["theoretical_forward_df"]["theoretical_forward"].to_numpy(dtype=float)
    wedge = (basis + credit + fric) / 1e4
    market = np.clip(theo * np.exp(wedge * years), *_FORWARD_RANGE)
    snapshot["market_forward_df"]["market_forward"] = market


def _validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(snapshot)
    out["spot_fx"] = float(np.clip(float(out["spot_fx"]), *_SPOT_RANGE))
    for df_key in ("huf_curve_df", "usd_curve_df"):
        curve = out[df_key].copy()
        curve["discount_factor"] = curve["discount_factor"].clip(1.0e-6, 1.0)
        curve["discount_factor"] = curve["discount_factor"].cummin()
        out[df_key] = curve

    basis_curve = out["basis_curve_df"].copy()
    basis_curve["basis_bps"] = basis_curve["basis_bps"].clip(*_BASIS_RANGE_BPS)
    basis_curve["implied_basis_decimal"] = basis_curve["basis_bps"] / 1e4
    out["basis_curve_df"] = basis_curve

    credit = out["credit_assumptions"].copy()
    credit["credit_spread_bps"] = credit["credit_spread_bps"].clip(*_CREDIT_RANGE_BPS)
    credit["credit_spread_decimal"] = credit["credit_spread_bps"] / 1e4
    out["credit_assumptions"] = credit

    fric = out["friction_assumptions"].copy()
    fric["funding_friction_bps"] = fric["funding_friction_bps"].clip(*_FRICTION_RANGE_BPS)
    fric["funding_friction_decimal"] = fric["funding_friction_bps"] / 1e4
    out["friction_assumptions"] = fric

    out["theoretical_forward_df"]["theoretical_forward"] = out["theoretical_forward_df"][
        "theoretical_forward"
    ].clip(*_FORWARD_RANGE)
    _recompute_forwards(out)
    return out


def build_custom_scenario(name: str, magnitude: float) -> Scenario:
    if name == "custom_parallel":
        return custom_parallel(
            huf_shift=magnitude,
            usd_shift=0.6 * magnitude,
            basis_shift=-8.0 * magnitude,
            credit_shift=6.0 * magnitude,
            funding_shift=5.0 * magnitude,
            liquidity_shift=-4.0 * magnitude,
        )
    if name == "custom_steepener":
        return custom_steepener(
            huf_front=-0.6 * magnitude,
            huf_back=0.9 * magnitude,
            usd_front=-0.35 * magnitude,
            usd_back=0.5 * magnitude,
        )
    if name == "custom_flattener":
        return custom_flattener(
            huf_front=0.8 * magnitude,
            huf_back=-0.6 * magnitude,
            usd_front=0.45 * magnitude,
            usd_back=-0.35 * magnitude,
        )
    raise ValueError(f"Unsupported custom scenario: {name}")


def apply_state_scenario(state: Mapping[str, Any], scenario: Scenario) -> dict[str, Any]:
    st = ensure_market_state(state)
    previous = deepcopy(st)

    baseline_shock_state = {
        "huf_rates": {"front": 0.0, "belly": 0.0, "back": 0.0},
        "usd_rates": {"front": 0.0, "belly": 0.0, "back": 0.0},
        "spot": 0.0,
        "basis_curve": {"front": 0.0, "belly": 0.0, "back": 0.0},
        "credit_spreads": {"sovereign": 0.0, "banks": 0.0},
        "funding_spreads": {"secured": 0.0, "unsecured": 0.0},
        "liquidity_repo_availability": 0.0,
    }
    shocked = apply_scenario(scenario, baseline_shock_state)
    delta = _scenario_to_delta(shocked)

    stressed_regime = clip_regime(
        {
            **st["regime"],
            "name": scenario.name,
            "level": st["regime"]["level"] + delta.level,
            "slope": st["regime"]["slope"] + delta.slope,
            "curvature": st["regime"]["curvature"] + delta.curvature,
        }
    )

    stressed = generate_market(
        seed=st["seed"],
        regime=stressed_regime,
        spot_fx=float(st["base_snapshot"]["spot_fx"] + delta.spot_shift),
        tenors=st["base_snapshot"]["tenors"],
    )

    years = stressed["basis_curve_df"]["years"].to_numpy(dtype=float)
    term_centered = years - years.mean()
    slope_term = term_centered / max(np.max(np.abs(term_centered)), 1.0)

    stressed["basis_curve_df"]["basis_bps"] += delta.basis_shift_bps + 0.5 * delta.basis_shift_bps * slope_term
    stressed["credit_assumptions"]["credit_spread_bps"] += delta.credit_shift_bps
    stressed["friction_assumptions"]["funding_friction_bps"] += delta.friction_shift_bps

    stressed = _validate_snapshot(stressed)

    next_state = ensure_market_state(previous)
    next_state["base_snapshot"] = deepcopy(previous["base_snapshot"])
    next_state["stressed_snapshot"] = stressed
    next_state["scenario"] = scenario.name
    return next_state


def summarize_for_shell(snapshot: Mapping[str, Any]) -> dict[str, float]:
    usd_curve = snapshot["usd_curve_df"].set_index("tenor")
    huf_curve = snapshot["huf_curve_df"].set_index("tenor")
    tenor_key = "1Y" if "1Y" in usd_curve.index else usd_curve.index[len(usd_curve) // 2]
    basis = snapshot["basis_curve_df"].set_index("tenor")
    return {
        "base_rate": float(usd_curve.loc[tenor_key, "usd_zero_rate"] * 100.0),
        "quote_rate": float(huf_curve.loc[tenor_key, "huf_zero_rate"] * 100.0),
        "spot_fx": float(snapshot["spot_fx"]),
        "cross_currency_basis_bps": float(basis.loc[tenor_key, "basis_bps"]),
    }


def apply_shell_patch(state: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    """Apply sidebar control patch to canonical state via one deterministic path."""
    st = ensure_market_state(state)
    next_state = ensure_market_state(st)
    base = deepcopy(next_state["base_snapshot"])

    one_y = "1Y"

    if "spot_fx" in patch:
        base["spot_fx"] = float(np.clip(float(patch["spot_fx"]), *_SPOT_RANGE))

    if "base_rate" in patch:
        usd_curve = base["usd_curve_df"].copy()
        idx = usd_curve["tenor"] == one_y
        if idx.any():
            target = float(patch["base_rate"]) / 100.0
            shift = target - float(usd_curve.loc[idx, "usd_zero_rate"].iloc[0])
            usd_curve.loc[:, "usd_zero_rate"] = usd_curve["usd_zero_rate"] + shift
            usd_curve.loc[:, "discount_factor"] = np.exp(-usd_curve["usd_zero_rate"] * usd_curve["years"])
            base["usd_curve_df"] = usd_curve

    if "quote_rate" in patch:
        huf_curve = base["huf_curve_df"].copy()
        idx = huf_curve["tenor"] == one_y
        if idx.any():
            target = float(patch["quote_rate"]) / 100.0
            shift = target - float(huf_curve.loc[idx, "huf_zero_rate"].iloc[0])
            huf_curve.loc[:, "huf_zero_rate"] = huf_curve["huf_zero_rate"] + shift
            huf_curve.loc[:, "discount_factor"] = np.exp(-huf_curve["huf_zero_rate"] * huf_curve["years"])
            base["huf_curve_df"] = huf_curve

    if "cross_currency_basis_bps" in patch:
        basis_curve = base["basis_curve_df"].copy()
        idx = basis_curve["tenor"] == one_y
        if idx.any():
            target_basis = float(patch["cross_currency_basis_bps"])
            shift = target_basis - float(basis_curve.loc[idx, "basis_bps"].iloc[0])
            basis_curve.loc[:, "basis_bps"] = basis_curve["basis_bps"] + shift
            basis_curve.loc[:, "implied_basis_decimal"] = basis_curve["basis_bps"] / 1e4
            base["basis_curve_df"] = basis_curve

    if "regime_name" in patch:
        regime_name = str(patch["regime_name"])
        current_regime = next_state["regime"]
        preset_regimes = {
            "calm": {**current_regime, "name": "calm", "level": -0.45, "slope": -0.15, "curvature": 0.05, "noise_scale": 0.7},
            "baseline": {**current_regime, "name": "baseline", "level": 0.0, "slope": 0.0, "curvature": 0.0, "noise_scale": 1.0},
            "stress": {**current_regime, "name": "stress", "level": 0.9, "slope": 0.25, "curvature": 0.25, "noise_scale": 1.6},
        }
        next_state["regime"] = clip_regime(preset_regimes.get(regime_name, preset_regimes["baseline"]))

    base = _validate_snapshot(base)
    next_state["base_snapshot"] = base
    next_state["stressed_snapshot"] = deepcopy(base)
    next_state["scenario"] = "none"

    if "selected_scenario" in patch:
        next_state["scenario"] = str(patch["selected_scenario"])
    if "role" in patch:
        next_state["user_role"] = str(patch["role"])
    if "learning_mode" in patch:
        next_state["learning_mode"] = str(patch["learning_mode"])

    return next_state


def make_stress_table(base_snapshot: Mapping[str, Any], stressed_snapshot: Mapping[str, Any]) -> pd.DataFrame:
    merged = base_snapshot["basis_curve_df"][["tenor", "basis_bps"]].merge(
        stressed_snapshot["basis_curve_df"][["tenor", "basis_bps"]],
        on="tenor",
        suffixes=("_base", "_stressed"),
    )
    merged["delta_bps"] = merged["basis_bps_stressed"] - merged["basis_bps_base"]
    return merged


__all__ = [
    "SCENARIO_LIBRARY",
    "apply_state_scenario",
    "build_custom_scenario",
    "clip_regime",
    "ensure_market_state",
    "make_stress_table",
    "regenerate_market_state",
    "apply_shell_patch",
    "summarize_for_shell",
]
