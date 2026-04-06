from __future__ import annotations

import streamlit as st

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_state_scenario,
    build_custom_scenario,
    clip_regime,
    ensure_market_state,
    regenerate_market_state,
    summarize_for_shell,
)

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
    **{name: name.replace("_", " ").title() for name in SCENARIO_LIBRARY},
    "custom_parallel": "Custom Parallel",
    "custom_steepener": "Custom Steepener",
    "custom_flattener": "Custom Flattener",
}



# Keep smoke-test stubs and cold imports resilient.
try:
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
except Exception:
    pass


def _button(label: str) -> bool:
    button_fn = getattr(st, "button", None)
    if callable(button_fn):
        return bool(button_fn(label))
    return False

def _sync_legacy_fields() -> None:
    summary = summarize_for_shell(st.session_state.market_state["base_snapshot"])
    st.session_state.base_rate = summary["base_rate"]
    st.session_state.quote_rate = summary["quote_rate"]
    st.session_state.spot_fx = summary["spot_fx"]
    st.session_state.cross_currency_basis_bps = int(round(summary["cross_currency_basis_bps"]))
    st.session_state.vol_regime = "Normal"

    # Legacy keys used by lesson pages.
    st.session_state.market_state["usd_rate"] = summary["base_rate"] / 100.0
    st.session_state.market_state["huf_rate"] = summary["quote_rate"] / 100.0
    st.session_state.market_state["basis_bps"] = summary["cross_currency_basis_bps"]
    st.session_state.market_state["spot_fx"] = summary["spot_fx"]


def ensure_market_state_initialized() -> None:
    defaults = {
        "mode": "Basic",
        "base_rate": 4.25,
        "quote_rate": 5.0,
        "spot_fx": 365.0,
        "cross_currency_basis_bps": -22,
        "vol_regime": "Normal",
        "suggested_page": LEARNING_PATH[0],
        "market_seed": 7,
        "custom_scenario_magnitude": 0.25,
        "selected_scenario": "none",
        "market_narrative": "Use sidebar controls to regenerate markets and apply scenarios.",
        "active_role": "treasury",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

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


def render_global_shell(*, page_context: str = "overview") -> None:
    """Render shared controls and a persistent suggested learning path."""
    _ = page_context
    ensure_market_state_initialized()

    with st.sidebar:
        st.header("Learning + Market Controls")
        st.session_state.mode = st.segmented_control(
            "Mode",
            options=["Basic", "Learning"],
            default=st.session_state.mode,
            help="Basic simplifies narrative. Learning adds rationale and extra interpretation.",
        )

        st.subheader("Regime generator")
        st.session_state.market_seed = int(
            st.number_input("Seed", min_value=0, max_value=999_999, value=int(st.session_state.market_seed), step=1)
        )

        regime = st.session_state.market_state["regime"]
        regime_name = st.selectbox("Regime preset", ["baseline", "calm", "stress"], index=0)
        level = st.slider("Level", -2.0, 2.0, float(regime.get("level", 0.0)), 0.05)
        slope = st.slider("Slope", -2.0, 2.0, float(regime.get("slope", 0.0)), 0.05)
        curvature = st.slider("Curvature", -2.0, 2.0, float(regime.get("curvature", 0.0)), 0.05)
        noise_scale = st.slider("Volatility / noise", 0.2, 3.0, float(regime.get("noise_scale", 1.0)), 0.05)
        liquidity = st.slider("Liquidity", 0.4, 2.0, float(regime.get("liquidity", 1.0)), 0.05)

        if _button("Regenerate market"):
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
        scenario_label = st.selectbox(
            "Scenario",
            list(SCENARIO_OPTIONS.values()),
            index=list(SCENARIO_OPTIONS.values()).index(selected_label),
        )
        scenario_name = next(key for key, value in SCENARIO_OPTIONS.items() if value == scenario_label)
        st.session_state.selected_scenario = scenario_name

        if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
            st.session_state.custom_scenario_magnitude = st.slider(
                "Custom magnitude", -1.5, 1.5, float(st.session_state.custom_scenario_magnitude), 0.05
            )

        if _button("Apply scenario"):
            scenario = _scenario_from_selection(scenario_name)
            if scenario is None:
                st.session_state.market_state["stressed_snapshot"] = st.session_state.market_state["base_snapshot"]
                st.session_state.market_state["scenario"] = "none"
            else:
                st.session_state.market_state = apply_state_scenario(st.session_state.market_state, scenario)
            _sync_legacy_fields()

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")

        st.caption(st.session_state.market_narrative)


def learning_hint(text: str) -> None:
    ensure_market_state_initialized()
    if st.session_state.get("mode", "Basic") == "Learning":
        st.info(text)
