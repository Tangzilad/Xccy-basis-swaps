from __future__ import annotations

from src.analytics.xccy_swap import SwapPeriod, cashflow_timeline, synthetic_funding_cost_outputs


def _as_decimal(rate_like: float) -> float:
    return rate_like / 100.0 if rate_like > 1 else rate_like


def _get_market_state(session_state: dict) -> dict:
    market_state = session_state.get("market_state")
    if isinstance(market_state, dict):
        return market_state
    state = {
        "spot_fx": float(session_state.get("spot_fx", 1.08)),
        "usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))),
        "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))),
        "basis_bps": float(session_state.get("cross_currency_basis_bps", -22)),
    }
    session_state["market_state"] = state
    return state


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="2. XCCY mechanics", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[1]
    m = _get_market_state(st.session_state)

    spot = float(m["spot_fx"])
    usd_rate = _as_decimal(float(m["usd_rate"]))
    huf_rate = _as_decimal(float(m["huf_rate"]))
    basis = float(m["basis_bps"]) / 10_000.0
    timeline = cashflow_timeline(10_000_000, spot, [SwapPeriod("1Y", 1.0, usd_rate, huf_rate)], basis)
    forward = spot * (1 + (huf_rate + basis)) / (1 + usd_rate)
    out = synthetic_funding_cost_outputs(spot, forward, huf_rate, basis, 1.0)

    st.title("2. XCCY mechanics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Spot", f"{spot:.4f}")
    c2.metric("Basis", f"{basis * 10_000:.1f} bps")
    c3.metric("Basis drag", f"{out['basis_drag_bp']:.2f} bps")
    st.bar_chart({"date": [x["date"] for x in timeline], "usd": [x["usd_cashflow"] for x in timeline]}, x="date")
    st.dataframe(timeline, use_container_width=True)
    st.write("Mechanics are shown from the USD-receiver / HUF-payer perspective.")
    learning_hint("Positive cashflows are received by the USD leg receiver.")
    render_calculation_windows([
        CalculationWindow("Synthetic USD (no basis)", r"r=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}", f"$S={spot:.4f}, F={forward:.4f}, r_{{HUF}}={huf_rate:.4%}$", ("Positive rate = higher funding cost.",), result=f"{out['synthetic_usd_rate_no_basis']:.4%}"),
        CalculationWindow("Synthetic USD (with basis)", r"r=\frac{\frac{1+(r_{HUF}+b)T}{F/S}-1}{T}", f"$b={basis:.4%}$", ("Positive basis increases HUF coupon.",), result=f"{out['synthetic_usd_rate_with_basis']:.4%}"),
        CalculationWindow("Basis drag", r"(r_{with}-r_{no})\times 10{,}000", f"$({out['synthetic_usd_rate_with_basis']:.6f}-{out['synthetic_usd_rate_no_basis']:.6f})\times10,000$", ("Positive drag means worse synthetic funding.",), result=f"{out['basis_drag_bp']:.2f} bp"),
    ])
