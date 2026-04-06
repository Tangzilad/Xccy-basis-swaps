from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import pandas as pd

from src.controllers.market_state_controller import ensure_market_state

_CANONICAL_TOP_LEVEL_KEYS = {"seed", "regime", "base_snapshot", "stressed_snapshot", "scenario"}


def _is_snapshot(snapshot: Mapping[str, Any] | None) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    required = {
        "spot_fx",
        "huf_curve_df",
        "usd_curve_df",
        "basis_curve_df",
        "market_forward_df",
        "theoretical_forward_df",
        "credit_assumptions",
        "friction_assumptions",
    }
    return required.issubset(snapshot.keys())


def is_canonical_market_state(state: Mapping[str, Any] | None) -> bool:
    if not isinstance(state, Mapping):
        return False
    if not _CANONICAL_TOP_LEVEL_KEYS.issubset(state.keys()):
        return False
    return _is_snapshot(state.get("base_snapshot")) and _is_snapshot(state.get("stressed_snapshot"))


def _legacy_to_partial_canonical(state: Mapping[str, Any], seed: int) -> dict[str, Any]:
    """Strict one-place converter for pre-canonical UI payloads.

    The converter only hydrates commonly used shallow fields and relies on
    `ensure_market_state` for canonical defaults/validation.
    """
    canonical = ensure_market_state(None, seed=seed)
    base = deepcopy(canonical["base_snapshot"])

    one_y = "1Y"
    usd_curve = base["usd_curve_df"]
    huf_curve = base["huf_curve_df"]
    basis_curve = base["basis_curve_df"]

    usd_rate = state.get("usd_rate", state.get("base_rate"))
    if usd_rate is not None:
        usd_dec = float(usd_rate) / 100.0 if float(usd_rate) > 1 else float(usd_rate)
        idx = usd_curve["tenor"] == one_y
        if idx.any():
            shift = usd_dec - float(usd_curve.loc[idx, "usd_zero_rate"].iloc[0])
            usd_curve.loc[:, "usd_zero_rate"] = usd_curve["usd_zero_rate"] + shift

    huf_rate = state.get("huf_rate", state.get("quote_rate"))
    if huf_rate is not None:
        huf_dec = float(huf_rate) / 100.0 if float(huf_rate) > 1 else float(huf_rate)
        idx = huf_curve["tenor"] == one_y
        if idx.any():
            shift = huf_dec - float(huf_curve.loc[idx, "huf_zero_rate"].iloc[0])
            huf_curve.loc[:, "huf_zero_rate"] = huf_curve["huf_zero_rate"] + shift

    if "basis_bps" in state or "cross_currency_basis_bps" in state:
        target_basis = float(state.get("basis_bps", state.get("cross_currency_basis_bps", 0.0)))
        idx = basis_curve["tenor"] == one_y
        if idx.any():
            shift = target_basis - float(basis_curve.loc[idx, "basis_bps"].iloc[0])
            basis_curve.loc[:, "basis_bps"] = basis_curve["basis_bps"] + shift
            basis_curve.loc[:, "implied_basis_decimal"] = basis_curve["basis_bps"] / 1e4

    if "spot_fx" in state:
        base["spot_fx"] = float(state["spot_fx"])

    canonical["base_snapshot"] = base
    canonical["stressed_snapshot"] = deepcopy(base)
    canonical["scenario"] = "none"
    return canonical


def normalize_session_market_state(session_state: Mapping[str, Any], *, seed: int = 7) -> dict[str, Any]:
    raw_state = session_state.get("market_state")

    if is_canonical_market_state(raw_state):
        canonical = ensure_market_state(raw_state, seed=seed)
    elif isinstance(raw_state, Mapping):
        canonical = ensure_market_state(_legacy_to_partial_canonical(raw_state, seed), seed=seed)
    else:
        canonical = ensure_market_state(None, seed=seed)

    session_state["market_state"] = canonical
    return canonical


def _summary_1y(snapshot: Mapping[str, Any]) -> dict[str, float]:
    def _pick(df: pd.DataFrame, column: str) -> float:
        idx = df["tenor"] == "1Y"
        if idx.any():
            return float(df.loc[idx, column].iloc[0])
        return float(df.iloc[len(df) // 2][column])

    return {
        "spot_fx": float(snapshot["spot_fx"]),
        "usd_rate": _pick(snapshot["usd_curve_df"], "usd_zero_rate"),
        "huf_rate": _pick(snapshot["huf_curve_df"], "huf_zero_rate"),
        "basis_bps": _pick(snapshot["basis_curve_df"], "basis_bps"),
        "market_forward": _pick(snapshot["market_forward_df"], "market_forward"),
        "theoretical_forward": _pick(snapshot["theoretical_forward_df"], "theoretical_forward"),
        "credit_spread_bps": _pick(snapshot["credit_assumptions"], "credit_spread_bps"),
        "funding_friction_bps": _pick(snapshot["friction_assumptions"], "funding_friction_bps"),
    }


def get_canonical_market_context(session_state: Mapping[str, Any], *, seed: int = 7) -> dict[str, Any]:
    state = normalize_session_market_state(session_state, seed=seed)
    base_snapshot = state["base_snapshot"]
    stressed_snapshot = state["stressed_snapshot"]
    return {
        "state": state,
        "base_snapshot": base_snapshot,
        "stressed_snapshot": stressed_snapshot,
        "summary_1y": {
            "base": _summary_1y(base_snapshot),
            "stressed": _summary_1y(stressed_snapshot),
        },
    }
