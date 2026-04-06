from __future__ import annotations

from src.analytics.conversion_factor import conversion_factor_from_fx
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.hedging import hedged_pickup_bp
from src.analytics.parity import fair_value_comparison
from src.analytics.xccy_swap import synthetic_funding_cost_outputs
from src.state.session_access import get_canonical_market_context


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
        "basis_bps": bps,
        "parity": parity,
        "frictions": fr,
        "conversion_factor": cf,
        "pickup_bp": pk,
        "synthetic": syn,
    }


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="7. HUF/USD strategy and stress lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[6]

    context = get_canonical_market_context(st.session_state)
    base_snapshot = context["base_snapshot"]
    stressed_snapshot = context["stressed_snapshot"]

    bm, sm = _compute_metrics(base_snapshot), _compute_metrics(stressed_snapshot)
    rows = [
        {
            "state": "base",
            "basis_bps": bm["basis_bps"],
            "pickup_bp": bm["pickup_bp"],
            "raw_wedge_bp": bm["parity"]["raw_basis_wedge_bp"],
        },
        {
            "state": "stressed",
            "basis_bps": sm["basis_bps"],
            "pickup_bp": sm["pickup_bp"],
            "raw_wedge_bp": sm["parity"]["raw_basis_wedge_bp"],
        },
    ]

    st.title("7. HUF/USD strategy and stress lab")
    st.caption(f"Scenario: {context['state'].get('scenario', 'none')}")
    a, b, c = st.columns(3)
    a.metric("Δ basis", f"{sm['basis_bps'] - bm['basis_bps']:.2f} bps")
    b.metric("Δ pickup", f"{sm['pickup_bp'] - bm['pickup_bp']:.2f} bps")
    c.metric("Stress actionable", "Yes" if sm["frictions"]["is_actionable"] else "No")
    st.bar_chart({"state": [r['state'] for r in rows], "basis_bps": [r['basis_bps'] for r in rows], "pickup_bp": [r['pickup_bp'] for r in rows], "raw_wedge_bp": [r['raw_wedge_bp'] for r in rows]}, x="state")
    st.dataframe(rows, use_container_width=True)
    st.write("Stress scenarios roll into parity, frictions, and pickup to assess strategy robustness.")
    learning_hint("Check whether net pickup survives widened friction bands.")
    render_calculation_windows([
        CalculationWindow("Stressed raw wedge", r"(r_{HUF}^{impl}-r_{HUF})\times10{,}000", f"$S={sm['spot']:.4f}, F={sm['forward']:.4f}$", ("Positive wedge means richer implied HUF.",), result=f"{sm['parity']['raw_basis_wedge_bp']:.2f} bps"),
        CalculationWindow("Stressed net edge", r"\text{Raw edge}-\text{Friction}", f"${sm['frictions']['raw_edge_bp']:.2f}-{sm['frictions']['total_friction_bp']:.2f}$", ("Costs reduce tradeability.",), result=f"{sm['frictions']['net_edge_bp']:.2f} bps"),
        CalculationWindow("Stressed hedged pickup", r"\text{Gross}-\text{hedge}-\text{basis}-\text{extra}", f"$CF={sm['conversion_factor']:.6f}, basis={abs(sm['basis_bps']):.2f}$", ("Positive pickup remains attractive.",), result=f"{sm['pickup_bp']:.2f} bps"),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
