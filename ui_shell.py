from __future__ import annotations

from typing import Any

import streamlit as st

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_shell_patch,
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
REGIME_OPTIONS = {"baseline": "Baseline", "calm": "Calm", "stress": "Stress"}
LEARNING_MODE_OPTIONS = ("Learning", "Basic")
ROLE_OPTIONS = ("Issuer", "Investor", "Treasury", "Arbitrageur")


def learning_hint(text: str) -> None:
    if st.session_state.get("mode", "Learning") == "Learning":
        st.info(text)


def _sync_sidebar_fields() -> None:
    context = get_canonical_market_context(st.session_state, seed=int(st.session_state["market_seed"]))
    summary = context["summary_1y"]["base"]
    st.session_state.base_rate = float(summary["usd_rate"] * 100.0)
    st.session_state.quote_rate = float(summary["huf_rate"] * 100.0)
    st.session_state.spot_fx = float(summary["spot_fx"])
    st.session_state.cross_currency_basis_bps = float(summary["basis_bps"])

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
    sidebar = getattr(st, "sidebar", st)
    number_input = getattr(sidebar, "number_input", getattr(st, "number_input", None))
    selectbox = getattr(sidebar, "selectbox", getattr(st, "selectbox", None))
    button = getattr(sidebar, "button", getattr(st, "button", None))
    expander = getattr(sidebar, "expander", getattr(st, "expander", None))

    scenario_keys = list(SCENARIO_OPTIONS.keys())
    current = st.session_state.get("selected_scenario", "none")
    default_index = scenario_keys.index(current) if current in scenario_keys else 0

    current_regime = str(st.session_state["market_state"]["regime"].get("name", "baseline")).lower()
    regime_index = list(REGIME_OPTIONS.keys()).index(current_regime) if current_regime in REGIME_OPTIONS else 0

    patch: dict[str, Any] = {}
    if callable(number_input):
        patch["spot_fx"] = number_input(
            "Spot HUF/USD",
            min_value=120.0,
            max_value=1200.0,
            value=float(st.session_state.get("spot_fx", 365.0)),
            step=0.25,
        )
        patch["quote_rate"] = number_input(
            "1Y HUF rate (%)",
            min_value=-2.0,
            max_value=30.0,
            value=float(st.session_state.get("quote_rate", 5.0)),
            step=0.05,
        )
        patch["base_rate"] = number_input(
            "1Y USD rate (%)",
            min_value=-2.0,
            max_value=20.0,
            value=float(st.session_state.get("base_rate", 4.25)),
            step=0.05,
        )
        patch["cross_currency_basis_bps"] = number_input(
            "1Y basis (bps)",
            min_value=-800.0,
            max_value=800.0,
            value=float(st.session_state.get("cross_currency_basis_bps", -22.0)),
            step=1.0,
        )

    if callable(selectbox):
        patch["regime_name"] = selectbox(
            "Regime selector",
            options=list(REGIME_OPTIONS.keys()),
            format_func=lambda k: REGIME_OPTIONS[k],
            index=regime_index,
        )
        scenario = selectbox(
            "Scenario picker",
            options=scenario_keys,
            format_func=lambda k: SCENARIO_OPTIONS[k],
            index=default_index,
        )
        patch["selected_scenario"] = scenario
        st.session_state.selected_scenario = scenario
        current_mode = st.session_state.get("mode", "Learning")
        patch["learning_mode"] = selectbox(
            "Learning mode",
            options=list(LEARNING_MODE_OPTIONS),
            index=LEARNING_MODE_OPTIONS.index(current_mode) if current_mode in LEARNING_MODE_OPTIONS else 0,
        )
        current_role = str(st.session_state.get("user_role", ROLE_OPTIONS[0]))
        patch["role"] = selectbox(
            "Role selector",
            options=list(ROLE_OPTIONS),
            index=ROLE_OPTIONS.index(current_role) if current_role in ROLE_OPTIONS else 0,
        )
    else:
        scenario = current

    slider = getattr(sidebar, "slider", getattr(st, "slider", None))
    if scenario.startswith("custom_") and callable(slider):
        st.session_state.custom_scenario_magnitude = slider(
            "Custom scenario magnitude",
            min_value=0.1,
            max_value=2.0,
            value=float(st.session_state.get("custom_scenario_magnitude", 0.5)),
            step=0.05,
        )

    if patch:
        st.session_state["market_state"] = apply_shell_patch(st.session_state["market_state"], patch)
        st.session_state.mode = patch.get("learning_mode", st.session_state.get("mode", "Learning"))
        st.session_state.user_role = patch.get("role", st.session_state.get("user_role", ROLE_OPTIONS[0]))

    if callable(button) and button("Regenerate market"):
        st.session_state["market_state"] = regenerate_market_state(st.session_state["market_state"])
        st.session_state.selected_scenario = "none"

    if callable(button) and button("Apply scenario"):
        chosen = _pick_scenario(scenario)
        if chosen is not None:
            st.session_state["market_state"] = apply_state_scenario(st.session_state["market_state"], chosen)

    if callable(expander):
        with expander("What changed?", expanded=False):
            st.write(
                "Inputs above mutate the canonical market state snapshot. All pages read the same shared snapshot "
                "and summary fields are refreshed from canonical context after every edit."
            )
        with expander("How to interpret the sign", expanded=False):
            st.write(
                "Positive basis means the market forward sits above pure parity after basis and frictions. "
                "Negative basis means the market forward is below that benchmark."
            )

    _sync_sidebar_fields()
