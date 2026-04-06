from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.conversion_factor import conversion_factor_from_fx
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.hedging import hedged_pickup_bp
from src.analytics.parity import fair_value_comparison
from src.analytics.xccy_swap import synthetic_funding_cost_outputs
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


def _compute_metrics(snapshot: dict) -> dict:
    usd_df = snapshot["usd_curve_df"].set_index("tenor")
    huf_df = snapshot["huf_curve_df"].set_index("tenor")
    basis_df = snapshot["basis_curve_df"].set_index("tenor")
    credit_df = snapshot["credit_assumptions"].set_index("tenor")
    friction_df = snapshot["friction_assumptions"].set_index("tenor")

    spot = float(snapshot["spot_fx"])
    usd = float(usd_df.loc["1Y", "usd_zero_rate"])
    huf = float(huf_df.loc["1Y", "huf_zero_rate"])
    bps = float(basis_df.loc["1Y", "basis_bps"])

    basis = bps / 10_000.0
    fwd = spot * (1 + (huf + basis)) / (1 + usd)
    parity = fair_value_comparison(spot, fwd, usd, huf, 1.0)

    fr = friction_adjusted_arbitrage_band_bp(
        abs(bps),
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.6,
        float(friction_df.loc["1Y", "funding_friction_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.4,
        3.0,
        8.0,
    )

    cf = conversion_factor_from_fx(spot, fwd)
    pk = hedged_pickup_bp((huf - usd) * 10_000 * cf, 40.0, abs(bps), fr["total_friction_bp"] * 0.1)
    syn = synthetic_funding_cost_outputs(spot, fwd, huf, basis, 1.0)
    return {
        "spot": spot,
        "forward": fwd,
        "usd_rate": usd,
        "huf_rate": huf,
        "basis_bps": bps,
        "parity": parity,
        "frictions": fr,
        "conversion_factor": cf,
        "pickup_bp": pk,
        "synthetic": syn,
    }


def render_page() -> None:
    st.set_page_config(page_title="7. HUF/USD strategy and stress lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[6]

    context = get_canonical_market_context(st.session_state)
    base_snapshot = context["base_snapshot"]
    stressed_snapshot = context["stressed_snapshot"]

    bm, sm = _compute_metrics(base_snapshot), _compute_metrics(stressed_snapshot)

    # --- Header with learning objectives ---
    render_page_header(6, "7. HUF/USD Strategy and Stress Lab")
    st.caption(f"Active scenario: **{context['state'].get('scenario', 'none')}**")

    # --- Delta metrics ---
    st.markdown("### Stress Impact Summary")
    a, b, c, d = st.columns(4)
    a.metric("Basis (base)", f"{bm['basis_bps']:.1f} bps")
    b.metric("Basis (stressed)", f"{sm['basis_bps']:.1f} bps", delta=f"{sm['basis_bps'] - bm['basis_bps']:.1f}")
    c.metric("Pickup (stressed)", f"{sm['pickup_bp']:.1f} bps", delta=f"{sm['pickup_bp'] - bm['pickup_bp']:.1f}")
    d.metric("Stress actionable", "Yes" if sm["frictions"]["is_actionable"] else "No")

    # --- Comparative table ---
    st.markdown("### Base vs Stressed Comparison")
    rows = [
        {
            "Metric": "Spot FX",
            "Base": f"{bm['spot']:.2f}",
            "Stressed": f"{sm['spot']:.2f}",
            "Delta": f"{sm['spot'] - bm['spot']:.2f}",
        },
        {
            "Metric": "USD rate",
            "Base": f"{bm['usd_rate']:.4%}",
            "Stressed": f"{sm['usd_rate']:.4%}",
            "Delta": f"{(sm['usd_rate'] - bm['usd_rate']) * 10000:.1f} bps",
        },
        {
            "Metric": "HUF rate",
            "Base": f"{bm['huf_rate']:.4%}",
            "Stressed": f"{sm['huf_rate']:.4%}",
            "Delta": f"{(sm['huf_rate'] - bm['huf_rate']) * 10000:.1f} bps",
        },
        {
            "Metric": "Basis (bps)",
            "Base": f"{bm['basis_bps']:.1f}",
            "Stressed": f"{sm['basis_bps']:.1f}",
            "Delta": f"{sm['basis_bps'] - bm['basis_bps']:.1f}",
        },
        {
            "Metric": "Raw wedge (bps)",
            "Base": f"{bm['parity']['raw_basis_wedge_bp']:.1f}",
            "Stressed": f"{sm['parity']['raw_basis_wedge_bp']:.1f}",
            "Delta": f"{sm['parity']['raw_basis_wedge_bp'] - bm['parity']['raw_basis_wedge_bp']:.1f}",
        },
        {
            "Metric": "Net edge (bps)",
            "Base": f"{bm['frictions']['net_edge_bp']:.1f}",
            "Stressed": f"{sm['frictions']['net_edge_bp']:.1f}",
            "Delta": f"{sm['frictions']['net_edge_bp'] - bm['frictions']['net_edge_bp']:.1f}",
        },
        {
            "Metric": "Hedged pickup (bps)",
            "Base": f"{bm['pickup_bp']:.1f}",
            "Stressed": f"{sm['pickup_bp']:.1f}",
            "Delta": f"{sm['pickup_bp'] - bm['pickup_bp']:.1f}",
        },
        {
            "Metric": "Actionable",
            "Base": "Yes" if bm["frictions"]["is_actionable"] else "No",
            "Stressed": "Yes" if sm["frictions"]["is_actionable"] else "No",
            "Delta": "--",
        },
    ]
    st.dataframe(rows, use_container_width=True)

    # --- Chart ---
    st.markdown("### Visual Comparison")
    chart_rows = [
        {"state": "Base", "Basis (bps)": bm["basis_bps"], "Pickup (bps)": bm["pickup_bp"], "Raw wedge (bps)": bm["parity"]["raw_basis_wedge_bp"]},
        {"state": "Stressed", "Basis (bps)": sm["basis_bps"], "Pickup (bps)": sm["pickup_bp"], "Raw wedge (bps)": sm["parity"]["raw_basis_wedge_bp"]},
    ]
    st.bar_chart(
        {
            "state": [r["state"] for r in chart_rows],
            "Basis (bps)": [r["Basis (bps)"] for r in chart_rows],
            "Pickup (bps)": [r["Pickup (bps)"] for r in chart_rows],
            "Raw wedge (bps)": [r["Raw wedge (bps)"] for r in chart_rows],
        },
        x="state",
    )

    # --- Strategy assessment ---
    st.markdown("### Strategy Assessment")
    pickup_survives = sm["pickup_bp"] > 0
    still_actionable = sm["frictions"]["is_actionable"]
    if pickup_survives and still_actionable:
        st.success(
            "Strategy **survives** the stress scenario: hedged pickup remains positive and "
            "the trade clears the friction band."
        )
    elif pickup_survives:
        st.warning(
            "Hedged pickup remains positive, but the trade no longer clears the friction band. "
            "Consider whether the edge justifies the execution risk."
        )
    else:
        st.error(
            "Strategy **fails** under stress: hedged pickup turns negative. "
            "The basis widening and friction increase erode all carry."
        )

    learning_hint(
        "This page integrates every concept from the prior lessons. "
        "The stress test reveals whether your understanding of mechanics, parity, funding, "
        "frictions, and hedging holds up when market conditions deteriorate. "
        "A robust strategy should maintain positive pickup even under the worst scenario."
    )

    # --- Calculation windows ---
    render_calculation_windows(
        [
            CalculationWindow(
                "Stressed raw wedge",
                r"(r_{HUF}^{impl}-r_{HUF})\times10{,}000",
                f"$S={sm['spot']:.4f}, F={sm['forward']:.4f}$",
                ("Positive wedge means richer implied HUF.",),
                result=f"{sm['parity']['raw_basis_wedge_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Stressed net edge",
                r"\text{Raw edge}-\text{Friction}",
                f"${sm['frictions']['raw_edge_bp']:.2f}-{sm['frictions']['total_friction_bp']:.2f}$",
                ("Costs reduce tradeability.",),
                result=f"{sm['frictions']['net_edge_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Stressed hedged pickup",
                r"\text{Gross}-\text{hedge}-\text{basis}-\text{extra}",
                f"$CF={sm['conversion_factor']:.6f}, basis={abs(sm['basis_bps']):.2f}$",
                ("Positive pickup remains attractive.",),
                result=f"{sm['pickup_bp']:.2f} bps",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(6)


if __name__ == "__main__":
    render_page()
else:
    render_page()
