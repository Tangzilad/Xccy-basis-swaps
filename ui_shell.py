from __future__ import annotations

import streamlit as st

LEARNING_PATH = [
    "1. Start here",
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]


def _init_defaults() -> None:
    defaults = {
        "mode": "Basic",
        "base_rate": 4.25,
        "quote_rate": 5.0,
        "spot_fx": 1.08,
        "cross_currency_basis_bps": -22,
        "vol_regime": "Normal",
        "suggested_page": LEARNING_PATH[0],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_global_shell() -> None:
    """Render shared controls and a persistent suggested learning path."""
    _init_defaults()

    with st.sidebar:
        st.header("Learning + Market Controls")
        st.session_state.mode = st.segmented_control(
            "Mode",
            options=["Basic", "Learning"],
            default=st.session_state.mode,
            help="Basic simplifies narrative. Learning adds rationale and extra interpretation.",
        )

        st.subheader("Global market-state controls")
        st.session_state.base_rate = st.slider(
            "Base currency policy rate (%)", 0.0, 12.0, float(st.session_state.base_rate), 0.05
        )
        st.session_state.quote_rate = st.slider(
            "Quote currency policy rate (%)", 0.0, 15.0, float(st.session_state.quote_rate), 0.05
        )
        st.session_state.spot_fx = st.number_input(
            "Spot FX", min_value=0.1000, max_value=50.0, value=float(st.session_state.spot_fx), step=0.0001
        )
        st.session_state.cross_currency_basis_bps = st.slider(
            "Cross-currency basis (bps)", -250, 250, int(st.session_state.cross_currency_basis_bps), 1
        )
        st.session_state.vol_regime = st.selectbox(
            "Volatility regime", ["Calm", "Normal", "Stressed"],
            index=["Calm", "Normal", "Stressed"].index(st.session_state.vol_regime),
        )

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")


def learning_hint(text: str) -> None:
    if st.session_state.get("mode", "Basic") == "Learning":
        st.info(text)
