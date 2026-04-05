from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

import numpy as np
import pandas as pd

from src.synthetic.market_generator import generate_market


@dataclass
class MarketState:
    valuation_date: str
    tenor_grid: list[str]
    spot_fx: float
    huf_usd_curves: dict[str, pd.DataFrame]
    theoretical_forwards: pd.DataFrame
    market_forwards: pd.DataFrame
    basis_curve: pd.DataFrame
    credit_funding_friction_assumptions: dict[str, pd.DataFrame]
    selected_scenario: str
    user_role: str
    hedge_settings: dict[str, Any]


def _normalize_regime_name(vol_regime: str) -> str:
    mapper = {
        "Calm": "calm",
        "Normal": "baseline",
        "Stressed": "stress",
    }
    return mapper.get(vol_regime, "baseline")


def _vol_from_scenario(selected_scenario: str) -> str:
    mapper = {
        "calm": "Calm",
        "baseline": "Normal",
        "stress": "Stressed",
    }
    return mapper.get(selected_scenario, "Normal")


def _ensure_copy_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy(deep=True).reset_index(drop=True)


def _rebuild_forwards(state: MarketState) -> None:
    years = state.theoretical_forwards["years"].to_numpy(dtype=float)
    usd_zero = state.huf_usd_curves["usd"]["usd_zero_rate"].to_numpy(dtype=float)
    huf_zero = state.huf_usd_curves["huf"]["huf_zero_rate"].to_numpy(dtype=float)
    basis = state.basis_curve["basis_bps"].to_numpy(dtype=float)

    credit = state.credit_funding_friction_assumptions["credit"]["credit_spread_bps"].to_numpy(dtype=float)
    friction = state.credit_funding_friction_assumptions["friction"]["funding_friction_bps"].to_numpy(dtype=float)

    theoretical = state.spot_fx * np.exp((huf_zero - usd_zero) * years)
    market = theoretical * np.exp((basis + credit + friction) / 1.0e4 * years)

    state.theoretical_forwards.loc[:, "theoretical_forward"] = theoretical
    state.market_forwards.loc[:, "market_forward"] = market


def init_market_state_from_generator(
    *,
    seed: int | None = 7,
    spot_fx: float = 365.0,
    vol_regime: str = "Normal",
    user_role: str = "Basic",
) -> MarketState:
    payload = generate_market(seed=seed, regime=_normalize_regime_name(vol_regime), spot_fx=spot_fx)

    huf_curve = _ensure_copy_df(payload["huf_curve_df"])
    usd_curve = _ensure_copy_df(payload["usd_curve_df"])
    basis_curve = _ensure_copy_df(payload["basis_curve_df"])
    theoretical_forwards = _ensure_copy_df(payload["theoretical_forward_df"])
    market_forwards = _ensure_copy_df(payload["market_forward_df"])
    credit_df = _ensure_copy_df(payload["credit_assumptions"])
    friction_df = _ensure_copy_df(payload["friction_assumptions"])

    hedge_settings = {
        "base_rate": float(usd_curve.iloc[0]["usd_zero_rate"] * 100.0),
        "quote_rate": float(huf_curve.iloc[0]["huf_zero_rate"] * 100.0),
        "cross_currency_basis_bps": int(round(float(basis_curve.iloc[0]["basis_bps"]))),
        "vol_regime": _vol_from_scenario(str(payload["regime_summary"]["name"])),
    }

    return MarketState(
        valuation_date=date.today().isoformat(),
        tenor_grid=list(payload["tenors"]),
        spot_fx=float(payload["spot_fx"]),
        huf_usd_curves={"huf": huf_curve, "usd": usd_curve},
        theoretical_forwards=theoretical_forwards,
        market_forwards=market_forwards,
        basis_curve=basis_curve,
        credit_funding_friction_assumptions={"credit": credit_df, "friction": friction_df},
        selected_scenario=str(payload["regime_summary"]["name"]),
        user_role=user_role,
        hedge_settings=hedge_settings,
    )


def serialize_market_state(state: MarketState) -> dict[str, Any]:
    return {
        "valuation_date": state.valuation_date,
        "tenor_grid": list(state.tenor_grid),
        "spot_fx": state.spot_fx,
        "huf_usd_curves": {name: frame.to_dict(orient="records") for name, frame in state.huf_usd_curves.items()},
        "theoretical_forwards": state.theoretical_forwards.to_dict(orient="records"),
        "market_forwards": state.market_forwards.to_dict(orient="records"),
        "basis_curve": state.basis_curve.to_dict(orient="records"),
        "credit_funding_friction_assumptions": {
            name: frame.to_dict(orient="records")
            for name, frame in state.credit_funding_friction_assumptions.items()
        },
        "selected_scenario": state.selected_scenario,
        "user_role": state.user_role,
        "hedge_settings": dict(state.hedge_settings),
    }


def apply_control_patch(state: MarketState, patch: Mapping[str, Any]) -> MarketState:
    if "mode" in patch:
        state.user_role = str(patch["mode"])

    if "spot_fx" in patch:
        state.spot_fx = float(patch["spot_fx"])

    if "vol_regime" in patch:
        vol_regime = str(patch["vol_regime"])
        state.hedge_settings["vol_regime"] = vol_regime
        state.selected_scenario = _normalize_regime_name(vol_regime)

    if "base_rate" in patch:
        target_usd = float(patch["base_rate"]) / 100.0
        usd_curve = state.huf_usd_curves["usd"]
        shift = target_usd - float(usd_curve.iloc[0]["usd_zero_rate"])
        usd_curve.loc[:, "usd_zero_rate"] = usd_curve["usd_zero_rate"] + shift
        state.hedge_settings["base_rate"] = float(patch["base_rate"])

    if "quote_rate" in patch:
        target_huf = float(patch["quote_rate"]) / 100.0
        huf_curve = state.huf_usd_curves["huf"]
        shift = target_huf - float(huf_curve.iloc[0]["huf_zero_rate"])
        huf_curve.loc[:, "huf_zero_rate"] = huf_curve["huf_zero_rate"] + shift
        state.hedge_settings["quote_rate"] = float(patch["quote_rate"])

    if "cross_currency_basis_bps" in patch:
        target_basis = float(patch["cross_currency_basis_bps"])
        shift = target_basis - float(state.basis_curve.iloc[0]["basis_bps"])
        state.basis_curve.loc[:, "basis_bps"] = state.basis_curve["basis_bps"] + shift
        state.basis_curve.loc[:, "implied_basis_decimal"] = state.basis_curve["basis_bps"] / 1.0e4
        state.hedge_settings["cross_currency_basis_bps"] = int(round(target_basis))

    _rebuild_forwards(state)
    return state


def snapshot_for_narrative(state: MarketState) -> dict[str, Any]:
    base_rate = float(state.huf_usd_curves["usd"].iloc[0]["usd_zero_rate"] * 100.0)
    quote_rate = float(state.huf_usd_curves["huf"].iloc[0]["huf_zero_rate"] * 100.0)
    basis_bps = float(state.basis_curve.iloc[0]["basis_bps"])
    vol_regime = str(state.hedge_settings.get("vol_regime", _vol_from_scenario(state.selected_scenario)))

    return {
        "valuation_date": state.valuation_date,
        "mode": state.user_role,
        "spot_fx": float(state.spot_fx),
        "base_rate": base_rate,
        "quote_rate": quote_rate,
        "cross_currency_basis_bps": basis_bps,
        "vol_regime": vol_regime,
        "selected_scenario": state.selected_scenario,
        "tenor_grid": list(state.tenor_grid),
    }
