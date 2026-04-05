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
