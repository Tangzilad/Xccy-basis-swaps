from __future__ import annotations

from src.analytics.xccy_swap import SwapPeriod, cashflow_timeline, synthetic_funding_cost_outputs
from src.state.session_access import get_canonical_market_context


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import (
        CalculationWindow,
        SignConventionContext,
        render_calculation_windows,
        render_shared_sign_convention,
    )
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="2. XCCY mechanics", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[1]

    context = get_canonical_market_context(st.session_state)
    summary = context["summary_1y"]["base"]

    spot = float(summary["spot_fx"])
    usd_rate = float(summary["usd_rate"])
    huf_rate = float(summary["huf_rate"])
    basis = float(summary["basis_bps"]) / 10_000.0

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
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="USD-receiver / HUF-payer swap leg direction.",
        positive_interpretation="Positive metric implies higher USD-side synthetic cost or inflow for the stated leg.",
        negative_interpretation="Negative metric implies lower USD-side synthetic cost or outflow for the stated leg.",
    )
    render_shared_sign_convention(sign_context)
    render_calculation_windows([
        CalculationWindow("Synthetic USD (no basis)", r"r=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}", f"$S={spot:.4f}, F={forward:.4f}, r_{{HUF}}={huf_rate:.4%}$", ("Positive rate = higher funding cost.",), result=f"{out['synthetic_usd_rate_no_basis']:.4%}"),
        CalculationWindow("Synthetic USD (with basis)", r"r=\frac{\frac{1+(r_{HUF}+b)T}{F/S}-1}{T}", f"$b={basis:.4%}$", ("Positive basis increases HUF coupon.",), result=f"{out['synthetic_usd_rate_with_basis']:.4%}"),
        CalculationWindow("Basis drag", r"(r_{with}-r_{no})\times 10{,}000", f"$({out['synthetic_usd_rate_with_basis']:.6f}-{out['synthetic_usd_rate_no_basis']:.6f})\times10,000$", ("Positive drag means worse synthetic funding.",), result=f"{out['basis_drag_bp']:.2f} bp"),
    ], sign_convention=sign_context)


if __name__ == "__main__":
    render_page()
else:
    render_page()
