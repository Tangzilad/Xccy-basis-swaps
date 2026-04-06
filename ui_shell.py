from __future__ import annotations

from typing import Any

import streamlit as st

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_state_scenario,
    build_custom_scenario,
    ensure_market_state,
    regenerate_market_state,
    summarize_for_shell,
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
    **{name: name.replace("_", " ").title() for name in SCENARIO_LIBRARY},
    "custom_parallel": "Custom parallel",
    "custom_steepener": "Custom steepener",
    "custom_flattener": "Custom flattener",
}


def learning_hint(text: str) -> None:
    if st.session_state.get("mode", "Learning") == "Learning":
        st.info(text)


def _sync_sidebar_fields() -> None:
    summary = summarize_for_shell(st.session_state["market_state"]["base_snapshot"])
    st.session_state.base_rate = float(summary["base_rate"])
    st.session_state.quote_rate = float(summary["quote_rate"])
    st.session_state.spot_fx = float(summary["spot_fx"])
    st.session_state.cross_currency_basis_bps = float(summary["cross_currency_basis_bps"])


    # Legacy convenience keys used by some pages.
    market_state = st.session_state["market_state"]
    market_state["usd_rate"] = st.session_state.base_rate / 100.0
    market_state["huf_rate"] = st.session_state.quote_rate / 100.0
    market_state["basis_bps"] = st.session_state.cross_currency_basis_bps
    market_state["spot_fx"] = st.session_state.spot_fx


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_seed", 7)
    st.session_state.setdefault("mode", "Learning")
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("selected_scenario", "none")
    st.session_state.setdefault("custom_scenario_magnitude", 0.5)
    st.session_state.setdefault("market_narrative", "Canonical market state drives all pages.")

    st.session_state["market_state"] = ensure_market_state(
        st.session_state.get("market_state"),
        seed=int(st.session_state["market_seed"]),
    )
    get_canonical_market_context(st.session_state, seed=int(st.session_state["market_seed"]))
    _sync_sidebar_fields()


def _pick_scenario(name: str) -> Any:
    if name in SCENARIO_LIBRARY:
        return SCENARIO_LIBRARY[name]
    if name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
        return build_custom_scenario(name, float(st.session_state.get("custom_scenario_magnitude", 0.5)))
    return None


def render_global_shell(*, page_context: str = "overview") -> None:
    _ = page_context
    ensure_market_state_initialized()

    scenario_keys = list(SCENARIO_OPTIONS.keys())
    current = st.session_state.get("selected_scenario", "none")
    default_index = scenario_keys.index(current) if current in scenario_keys else 0

    selectbox = getattr(st, "selectbox", None)
    if callable(selectbox):
        scenario = selectbox(
            "Scenario",
            options=scenario_keys,
            format_func=lambda k: SCENARIO_OPTIONS[k],
            index=default_index,
        )
        st.session_state.selected_scenario = scenario
    else:
        scenario = current

    slider = getattr(st, "slider", None)
    if scenario.startswith("custom_") and callable(slider):
        st.session_state.custom_scenario_magnitude = slider(
            "Custom scenario magnitude",
            min_value=0.1,
            max_value=2.0,
            value=float(st.session_state.get("custom_scenario_magnitude", 0.5)),
            step=0.05,
        )

    button = getattr(st, "button", None)
    if callable(button) and button("Regenerate market"):
        st.session_state["market_state"] = regenerate_market_state(st.session_state["market_state"])
        st.session_state.selected_scenario = "none"

    if callable(button) and button("Apply scenario"):
        chosen = _pick_scenario(scenario)
        if chosen is not None:
            st.session_state["market_state"] = apply_state_scenario(st.session_state["market_state"], chosen)

    _sync_sidebar_fields()
