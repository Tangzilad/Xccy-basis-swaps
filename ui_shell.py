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
    "8. Consolidated dashboard",
    "9. Glossary",
]

# Maps page indices (0-based, matching LEARNING_PATH step numbers) to page labels.
_PAGE_LABELS = {
    0: "Start here",
    1: "XCCY mechanics",
    2: "Parity lab",
    3: "Funding transformation",
    4: "Persistence / XVA",
    5: "Hedged pickup",
    6: "Strategy & stress",
    7: "Dashboard",
    8: "Glossary",
}

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


def _mark_page_visited(page_index: int) -> None:
    """Track which pages the user has visited for progress display."""
    visited = st.session_state.get("visited_pages", set())
    if not isinstance(visited, set):
        visited = set(visited)
    visited.add(page_index)
    st.session_state["visited_pages"] = visited


def _render_progress_tracker() -> None:
    """Show a visual progress tracker in the sidebar."""
    visited = st.session_state.get("visited_pages", set())
    if not isinstance(visited, set):
        visited = set(visited)

    total = len(_PAGE_LABELS)
    completed = len(visited & set(_PAGE_LABELS.keys()))
    pct = completed / total if total > 0 else 0

    st.sidebar.markdown("### Progress")
    st.sidebar.progress(pct, text=f"{completed}/{total} lessons visited")

    for idx, label in _PAGE_LABELS.items():
        marker = "~~" if idx in visited else ""
        check = " :white_check_mark:" if idx in visited else ""
        st.sidebar.caption(f"{marker}{idx}. {label}{marker}{check}")


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_seed", 7)
    st.session_state.setdefault("mode", "Learning")
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("selected_scenario", "none")
    st.session_state.setdefault("custom_scenario_magnitude", 0.5)
    st.session_state.setdefault("market_narrative", "Canonical market state drives all pages.")
    st.session_state.setdefault("visited_pages", set())

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

    # Determine current page index for progress tracking.
    suggested = st.session_state.get("suggested_page", LEARNING_PATH[0])
    for i, step in enumerate(LEARNING_PATH):
        if step == suggested:
            _mark_page_visited(i)
            break

    # --- Mode selector ---
    st.sidebar.markdown("### Settings")
    mode = st.sidebar.radio("Mode", ["Learning", "Basic"], index=0 if st.session_state.get("mode") == "Learning" else 1)
    st.session_state["mode"] = mode

    # --- Scenario controls ---
    st.sidebar.markdown("### Scenario")
    scenario_keys = list(SCENARIO_OPTIONS.keys())
    current = st.session_state.get("selected_scenario", "none")
    default_index = scenario_keys.index(current) if current in scenario_keys else 0

    scenario = st.sidebar.selectbox(
        "Scenario",
        options=scenario_keys,
        format_func=lambda k: SCENARIO_OPTIONS[k],
        index=default_index,
    )
    st.session_state.selected_scenario = scenario

    if scenario.startswith("custom_"):
        st.session_state.custom_scenario_magnitude = st.sidebar.slider(
            "Custom scenario magnitude",
            min_value=0.1,
            max_value=2.0,
            value=float(st.session_state.get("custom_scenario_magnitude", 0.5)),
            step=0.05,
        )

    if st.sidebar.button("Regenerate market"):
        st.session_state["market_state"] = regenerate_market_state(st.session_state["market_state"])
        st.session_state.selected_scenario = "none"

    if st.sidebar.button("Apply scenario"):
        chosen = _pick_scenario(scenario)
        if chosen is not None:
            st.session_state["market_state"] = apply_state_scenario(st.session_state["market_state"], chosen)

    _sync_sidebar_fields()

    # --- Progress tracker ---
    _render_progress_tracker()
