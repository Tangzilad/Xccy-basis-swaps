from __future__ import annotations

from copy import deepcopy

import streamlit as st

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_state_scenario,
    build_custom_scenario,
    clip_regime,
    regenerate_market_state,
)
from src.state.session_access import get_canonical_market_context

LEARNING_PATH = [
    "1. Start here",
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]

SCENARIO_OPTIONS = {
    "none": "No scenario",
    "parallel_up": "Parallel up",
    "parallel_down": "Parallel down",
    "steepener": "Steepener",
    "flattener": "Flattener",
    "funding_stress": "Funding stress",
    "credit_widening": "Credit widening",
    "liquidity_crunch": "Liquidity crunch",
    "custom_parallel": "Custom parallel",
    "custom_steepener": "Custom steepener",
    "custom_flattener": "Custom flattener",
}


def _apply_curve_controls(*, base_snapshot: dict, spot_fx: float, usd_rate_pct: float, huf_rate_pct: float, basis_bps: float) -> dict:
    out = deepcopy(base_snapshot)
    usd_curve = out["usd_curve_df"]
    huf_curve = out["huf_curve_df"]
    basis_curve = out["basis_curve_df"]

    one_y = "1Y"
    usd_idx = usd_curve["tenor"] == one_y
    huf_idx = huf_curve["tenor"] == one_y
    basis_idx = basis_curve["tenor"] == one_y

    if usd_idx.any():
        target = float(usd_rate_pct) / 100.0
        shift = target - float(usd_curve.loc[usd_idx, "usd_zero_rate"].iloc[0])
        usd_curve.loc[:, "usd_zero_rate"] = usd_curve["usd_zero_rate"] + shift

    if huf_idx.any():
        target = float(huf_rate_pct) / 100.0
        shift = target - float(huf_curve.loc[huf_idx, "huf_zero_rate"].iloc[0])
        huf_curve.loc[:, "huf_zero_rate"] = huf_curve["huf_zero_rate"] + shift

    if basis_idx.any():
        shift = float(basis_bps) - float(basis_curve.loc[basis_idx, "basis_bps"].iloc[0])
        basis_curve.loc[:, "basis_bps"] = basis_curve["basis_bps"] + shift
        basis_curve.loc[:, "implied_basis_decimal"] = basis_curve["basis_bps"] / 1e4

    out["spot_fx"] = float(spot_fx)

    years = out["basis_curve_df"]["years"].to_numpy(dtype=float)
    basis = out["basis_curve_df"]["basis_bps"].to_numpy(dtype=float)
    credit = out["credit_assumptions"]["credit_spread_bps"].to_numpy(dtype=float)
    fric = out["friction_assumptions"]["funding_friction_bps"].to_numpy(dtype=float)
    theo = out["theoretical_forward_df"]["theoretical_forward"].to_numpy(dtype=float)
    out["market_forward_df"]["market_forward"] = theo * __import__("numpy").exp((basis + credit + fric) / 1e4 * years)
    return out


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_seed", 7)
    st.session_state.setdefault("mode", "Basic")
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("selected_scenario", "none")
    st.session_state.setdefault("custom_scenario_magnitude", 0.5)
    st.session_state.setdefault("market_narrative", "Canonical market state drives all pages.")
    get_canonical_market_context(st.session_state, seed=int(st.session_state.market_seed))


def _scenario_from_selection(scenario_name: str):
    if scenario_name in SCENARIO_LIBRARY:
        return SCENARIO_LIBRARY[scenario_name]
    if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
        return build_custom_scenario(scenario_name, float(st.session_state.custom_scenario_magnitude))
    return None


def render_global_shell(*, page_context: str = "overview") -> None:
    _ = page_context
    ensure_market_state_initialized()
    context = get_canonical_market_context(st.session_state, seed=int(st.session_state.market_seed))
    state = context["state"]
    base_summary = context["summary_1y"]["base"]

    with st.sidebar:
        st.header("Learning + Market Controls")
        st.session_state.mode = st.segmented_control(
            "Mode", options=["Basic", "Learning"], default=st.session_state.mode
        )

        st.subheader("Global market-state controls")
        base_rate = st.slider("Base currency policy rate (%)", 0.0, 12.0, float(base_summary["usd_rate"] * 100.0), 0.05)
        quote_rate = st.slider("Quote currency policy rate (%)", 0.0, 15.0, float(base_summary["huf_rate"] * 100.0), 0.05)
        spot_fx = st.number_input("Spot FX", min_value=120.0, max_value=1200.0, value=float(base_summary["spot_fx"]), step=0.01)
        basis_bps = st.slider("Cross-currency basis (bps)", -250, 250, int(round(float(base_summary["basis_bps"]))), 1)

        if st.button("Apply global controls"):
            state["base_snapshot"] = _apply_curve_controls(
                base_snapshot=state["base_snapshot"],
                spot_fx=float(spot_fx),
                usd_rate_pct=float(base_rate),
                huf_rate_pct=float(quote_rate),
                basis_bps=float(basis_bps),
            )
            state["stressed_snapshot"] = deepcopy(state["base_snapshot"])
            state["scenario"] = "none"
            st.session_state.market_state = state

        regime = st.session_state.market_state["regime"]
        st.subheader("Regime controls")
        regime_name = st.selectbox("Regime preset", ["baseline", "calm", "stress"], index=0)
        level = st.slider("Level", -2.0, 2.0, float(regime.get("level", 0.0)), 0.05)
        slope = st.slider("Slope", -2.0, 2.0, float(regime.get("slope", 0.0)), 0.05)
        curvature = st.slider("Curvature", -2.0, 2.0, float(regime.get("curvature", 0.0)), 0.05)
        noise_scale = st.slider("Volatility / noise", 0.2, 3.0, float(regime.get("noise_scale", 1.0)), 0.05)
        liquidity = st.slider("Liquidity", 0.4, 2.0, float(regime.get("liquidity", 1.0)), 0.05)

        if st.button("Regenerate market"):
            st.session_state.market_state["seed"] = int(st.session_state.market_seed)
            st.session_state.market_state["regime"] = clip_regime(
                {
                    "name": regime_name,
                    "level": level,
                    "slope": slope,
                    "curvature": curvature,
                    "noise_scale": noise_scale,
                    "liquidity": liquidity,
                }
            )
            st.session_state.market_state = regenerate_market_state(st.session_state.market_state)

        st.subheader("Scenario selector")
        selected_label = SCENARIO_OPTIONS.get(st.session_state.selected_scenario, "No scenario")
        scenario_label = st.selectbox("Scenario", list(SCENARIO_OPTIONS.values()), index=list(SCENARIO_OPTIONS.values()).index(selected_label))
        scenario_name = next(key for key, value in SCENARIO_OPTIONS.items() if value == scenario_label)
        st.session_state.selected_scenario = scenario_name

        if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
            st.session_state.custom_scenario_magnitude = st.slider("Custom magnitude", -1.5, 1.5, float(st.session_state.custom_scenario_magnitude), 0.05)

        if st.button("Apply scenario"):
            scenario = _scenario_from_selection(scenario_name)
            if scenario is None:
                st.session_state.market_state["stressed_snapshot"] = deepcopy(st.session_state.market_state["base_snapshot"])
                st.session_state.market_state["scenario"] = "none"
            else:
                st.session_state.market_state = apply_state_scenario(st.session_state.market_state, scenario)

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")


def learning_hint(text: str) -> None:
    ensure_market_state_initialized()
    if st.session_state.get("mode", "Basic") == "Learning":
        st.info(text)
