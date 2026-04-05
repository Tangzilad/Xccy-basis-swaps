from __future__ import annotations

import streamlit as st

from src.state.market_state import apply_control_patch, init_market_state_from_generator, snapshot_for_narrative

LEARNING_PATH = [
    "1. Start here",
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_state", init_market_state_from_generator())
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])

    st.session_state.market_state = ensure_market_state(
        st.session_state.get("market_state"), seed=st.session_state.market_seed
    )
    _sync_legacy_fields()


def _scenario_from_selection(scenario_name: str):
    if scenario_name in SCENARIO_LIBRARY:
        return SCENARIO_LIBRARY[scenario_name]
    if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
        return build_custom_scenario(scenario_name, float(st.session_state.custom_scenario_magnitude))
    return None


def render_global_shell() -> None:
    """Render shared controls and a persistent suggested learning path."""
    ensure_market_state_initialized()
    state = st.session_state["market_state"]
    snapshot = snapshot_for_narrative(state)

    with st.sidebar:
        st.header("Learning + Market Controls")
        mode = st.segmented_control(
            "Mode",
            options=["Basic", "Learning"],
            default=snapshot["mode"],
            help="Basic simplifies narrative. Learning adds rationale and extra interpretation.",
        )

        st.subheader("Global market-state controls")
        base_rate = st.slider("Base currency policy rate (%)", 0.0, 12.0, float(snapshot["base_rate"]), 0.05)
        quote_rate = st.slider("Quote currency policy rate (%)", 0.0, 15.0, float(snapshot["quote_rate"]), 0.05)
        spot_fx = st.number_input(
            "Spot FX", min_value=120.0, max_value=1200.0, value=float(snapshot["spot_fx"]), step=0.0001
        )
        basis_bps = st.slider(
            "Cross-currency basis (bps)", -250, 250, int(round(float(snapshot["cross_currency_basis_bps"]))), 1
        )
        vol_regime = st.selectbox(
            "Volatility regime",
            ["Calm", "Normal", "Stressed"],
            index=["Calm", "Normal", "Stressed"].index(str(snapshot["vol_regime"])),
        )

        apply_control_patch(
            state,
            {
                "mode": mode,
                "base_rate": base_rate,
                "quote_rate": quote_rate,
                "spot_fx": spot_fx,
                "cross_currency_basis_bps": basis_bps,
                "vol_regime": vol_regime,
            },
        )

        regime = st.session_state.market_state["regime"]
        regime_name = st.selectbox("Regime preset", ["baseline", "calm", "stress"], index=0)
        level = st.slider("Level", -2.0, 2.0, float(regime.get("level", 0.0)), 0.05)
        slope = st.slider("Slope", -2.0, 2.0, float(regime.get("slope", 0.0)), 0.05)
        curvature = st.slider("Curvature", -2.0, 2.0, float(regime.get("curvature", 0.0)), 0.05)
        noise_scale = st.slider("Volatility / noise", 0.2, 3.0, float(regime.get("noise_scale", 1.0)), 0.05)
        liquidity = st.slider("Liquidity", 0.4, 2.0, float(regime.get("liquidity", 1.0)), 0.05)

        if st.button("Regenerate market"):
            st.session_state.market_state["seed"] = st.session_state.market_seed
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
            _sync_legacy_fields()

        st.divider()
        st.subheader("Scenario selector")
        selected_label = SCENARIO_OPTIONS.get(st.session_state.selected_scenario, "No scenario")
        scenario_label = st.selectbox("Scenario", list(SCENARIO_OPTIONS.values()), index=list(SCENARIO_OPTIONS.values()).index(selected_label))
        scenario_name = next(key for key, value in SCENARIO_OPTIONS.items() if value == scenario_label)
        st.session_state.selected_scenario = scenario_name

        if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
            st.session_state.custom_scenario_magnitude = st.slider(
                "Custom magnitude", -1.5, 1.5, float(st.session_state.custom_scenario_magnitude), 0.05
            )

        if st.button("Apply scenario"):
            scenario = _scenario_from_selection(scenario_name)
            if scenario is None:
                st.session_state.market_state["stressed_snapshot"] = st.session_state.market_state["base_snapshot"]
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
    snapshot = snapshot_for_narrative(st.session_state["market_state"])
    if snapshot["mode"] == "Learning":
        st.info(text)
