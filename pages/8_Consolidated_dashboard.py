"""Consolidated Dashboard -- all key outputs from every lesson in a single view.

This page does not introduce new analytics. Instead, it pulls together the most
important metrics from each lesson so learners can see how all the pieces fit
together and how they change under different scenarios.
"""

from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_header
from src.analytics.conversion_factor import conversion_factor_from_fx, translate_spread_bp
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.funding import build_tenor_funding_table, issuance_choice
from src.analytics.hedging import hedged_pickup_bp
from src.analytics.parity import fair_value_comparison
from src.analytics.xccy_swap import synthetic_funding_cost_outputs
from src.state.session_access import get_canonical_market_context
from ui_shell import ensure_market_state_initialized, learning_hint, render_global_shell


def _snapshot_metrics(snapshot: dict) -> dict:
    """Compute all key metrics from a single snapshot."""
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

    # --- Mechanics ---
    fwd = spot * (1 + (huf + basis)) / (1 + usd)
    syn = synthetic_funding_cost_outputs(spot, fwd, huf, basis, 1.0)

    # --- Parity ---
    parity = fair_value_comparison(spot, fwd, usd, huf, 1.0)

    # --- Funding ---
    extra = 12.0 / 10_000.0
    fund_rows = build_tenor_funding_table(
        domestic_label="HUF",
        foreign_label="USD",
        domestic_curve_rate=huf,
        foreign_curve_rate=usd,
        basis_spread=basis,
        extra_spread=extra,
        tenors=("1Y",),
        tenor_scales=(1.0,),
    )
    fund_1y = fund_rows[0]
    huf_choice = issuance_choice(
        issue_currency="HUF",
        direct_rate=float(fund_1y["HUF direct"]),
        swapped_rate=float(fund_1y["HUF synthetic"]),
    )

    # --- Frictions ---
    fr = friction_adjusted_arbitrage_band_bp(
        abs(bps),
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.6,
        float(friction_df.loc["1Y", "funding_friction_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.4,
        3.0,
        8.0,
    )

    # --- Hedging ---
    cf = conversion_factor_from_fx(spot, fwd)
    gross = translate_spread_bp((huf - usd) * 10_000, cf)
    pk = hedged_pickup_bp(gross, 40.0, abs(bps), fr["total_friction_bp"] * 0.1)

    return {
        "spot": spot,
        "forward": fwd,
        "usd_rate": usd,
        "huf_rate": huf,
        "basis_bps": bps,
        "basis_drag_bp": syn["basis_drag_bp"],
        "synthetic_usd_rate": syn["synthetic_usd_rate_with_basis"],
        "raw_wedge_bp": parity["raw_basis_wedge_bp"],
        "cip_forward": parity["fair_forward_no_basis"],
        "funding_gap_bp": float(fund_1y["HUF delta"]) * 10_000,
        "preferred_route": huf_choice.preferred_route,
        "total_friction_bp": fr["total_friction_bp"],
        "net_edge_bp": fr["net_edge_bp"],
        "is_actionable": fr["is_actionable"],
        "conversion_factor": cf,
        "gross_pickup_bp": gross,
        "hedged_pickup_bp": pk,
    }


def render_page() -> None:
    st.set_page_config(page_title="Consolidated Dashboard", page_icon="📊", layout="wide")
    ensure_market_state_initialized()
    render_global_shell()
    st.session_state.suggested_page = "8. Consolidated dashboard"

    context = get_canonical_market_context(st.session_state)
    base_summary = context["summary_1y"]["base"]
    base_snapshot = context["base_snapshot"]
    stressed_snapshot = context["stressed_snapshot"]
    bm = _snapshot_metrics(base_snapshot)
    sm = _snapshot_metrics(stressed_snapshot)

    render_page_header(6, "Consolidated Dashboard", show_objectives=False)
    st.caption(
        "All key outputs from every lesson in one view. "
        "Use the sidebar to change scenarios and see how metrics flow through."
    )
    st.caption(
        f"Canonical 1Y anchor: spot={base_summary['spot_fx']:.2f}, "
        f"USD={base_summary['usd_rate']:.2%}, HUF={base_summary['huf_rate']:.2%}, "
        f"basis={base_summary['basis_bps']:.1f} bps."
    )

    # ---- Section 1: Market State ----
    st.markdown("---")
    st.markdown("### 1. Market State")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot FX", f"{bm['spot']:.2f}", delta=f"{sm['spot'] - bm['spot']:.2f}" if sm['spot'] != bm['spot'] else None)
    c2.metric("USD rate", f"{bm['usd_rate']:.4%}", delta=f"{(sm['usd_rate'] - bm['usd_rate'])*10000:.1f} bps" if sm['usd_rate'] != bm['usd_rate'] else None)
    c3.metric("HUF rate", f"{bm['huf_rate']:.4%}", delta=f"{(sm['huf_rate'] - bm['huf_rate'])*10000:.1f} bps" if sm['huf_rate'] != bm['huf_rate'] else None)
    c4.metric("Basis (1Y)", f"{bm['basis_bps']:.1f} bps", delta=f"{sm['basis_bps'] - bm['basis_bps']:.1f}" if sm['basis_bps'] != bm['basis_bps'] else None)

    # ---- Section 2: XCCY Mechanics (from lesson 2) ----
    st.markdown("---")
    st.markdown("### 2. XCCY Mechanics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Forward (1Y)", f"{bm['forward']:.4f}")
    c2.metric("Synthetic USD rate", f"{bm['synthetic_usd_rate']:.4%}")
    c3.metric("Basis drag", f"{bm['basis_drag_bp']:.2f} bps", delta=f"{sm['basis_drag_bp'] - bm['basis_drag_bp']:.2f}" if sm['basis_drag_bp'] != bm['basis_drag_bp'] else None)

    # ---- Section 3: Parity (from lesson 3) ----
    st.markdown("---")
    st.markdown("### 3. Parity")
    c1, c2, c3 = st.columns(3)
    c1.metric("CIP fair forward", f"{bm['cip_forward']:.4f}")
    c2.metric("Observed forward", f"{bm['forward']:.4f}")
    c3.metric("Raw wedge", f"{bm['raw_wedge_bp']:.2f} bps", delta=f"{sm['raw_wedge_bp'] - bm['raw_wedge_bp']:.2f}" if sm['raw_wedge_bp'] != bm['raw_wedge_bp'] else None)

    # ---- Section 4: Funding Transformation (from lesson 4) ----
    st.markdown("---")
    st.markdown("### 4. Funding Transformation")
    c1, c2 = st.columns(2)
    c1.metric("Funding gap (1Y)", f"{bm['funding_gap_bp']:.1f} bps", delta=f"{sm['funding_gap_bp'] - bm['funding_gap_bp']:.1f}" if sm['funding_gap_bp'] != bm['funding_gap_bp'] else None)
    c2.metric("Preferred route", bm["preferred_route"])

    # ---- Section 5: Frictions (from lesson 5) ----
    st.markdown("---")
    st.markdown("### 5. Frictions & Arbitrage Limits")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total friction", f"{bm['total_friction_bp']:.1f} bps")
    c2.metric("Net edge", f"{bm['net_edge_bp']:.1f} bps", delta=f"{sm['net_edge_bp'] - bm['net_edge_bp']:.1f}" if sm['net_edge_bp'] != bm['net_edge_bp'] else None)
    c3.metric("Actionable (base)", "Yes" if bm["is_actionable"] else "No")

    # ---- Section 6: Hedging (from lesson 6) ----
    st.markdown("---")
    st.markdown("### 6. Hedged Pickup")
    c1, c2, c3 = st.columns(3)
    c1.metric("Conversion factor", f"{bm['conversion_factor']:.6f}")
    c2.metric("Gross pickup", f"{bm['gross_pickup_bp']:.1f} bps")
    c3.metric("Net hedged pickup", f"{bm['hedged_pickup_bp']:.1f} bps", delta=f"{sm['hedged_pickup_bp'] - bm['hedged_pickup_bp']:.1f}" if sm['hedged_pickup_bp'] != bm['hedged_pickup_bp'] else None)

    # ---- Section 7: Stress Summary (from lesson 7) ----
    st.markdown("---")
    st.markdown("### 7. Stress Summary")
    scenario_name = context["state"].get("scenario", "none")
    st.caption(f"Active scenario: **{scenario_name}**")

    summary_rows = [
        {"Metric": "Spot FX", "Base": f"{bm['spot']:.2f}", "Stressed": f"{sm['spot']:.2f}", "Delta": f"{sm['spot'] - bm['spot']:.2f}"},
        {"Metric": "Basis (bps)", "Base": f"{bm['basis_bps']:.1f}", "Stressed": f"{sm['basis_bps']:.1f}", "Delta": f"{sm['basis_bps'] - bm['basis_bps']:.1f}"},
        {"Metric": "Raw wedge (bps)", "Base": f"{bm['raw_wedge_bp']:.1f}", "Stressed": f"{sm['raw_wedge_bp']:.1f}", "Delta": f"{sm['raw_wedge_bp'] - bm['raw_wedge_bp']:.1f}"},
        {"Metric": "Basis drag (bps)", "Base": f"{bm['basis_drag_bp']:.2f}", "Stressed": f"{sm['basis_drag_bp']:.2f}", "Delta": f"{sm['basis_drag_bp'] - bm['basis_drag_bp']:.2f}"},
        {"Metric": "Funding gap (bps)", "Base": f"{bm['funding_gap_bp']:.1f}", "Stressed": f"{sm['funding_gap_bp']:.1f}", "Delta": f"{sm['funding_gap_bp'] - bm['funding_gap_bp']:.1f}"},
        {"Metric": "Total friction (bps)", "Base": f"{bm['total_friction_bp']:.1f}", "Stressed": f"{sm['total_friction_bp']:.1f}", "Delta": f"{sm['total_friction_bp'] - bm['total_friction_bp']:.1f}"},
        {"Metric": "Net edge (bps)", "Base": f"{bm['net_edge_bp']:.1f}", "Stressed": f"{sm['net_edge_bp']:.1f}", "Delta": f"{sm['net_edge_bp'] - bm['net_edge_bp']:.1f}"},
        {"Metric": "Hedged pickup (bps)", "Base": f"{bm['hedged_pickup_bp']:.1f}", "Stressed": f"{sm['hedged_pickup_bp']:.1f}", "Delta": f"{sm['hedged_pickup_bp'] - bm['hedged_pickup_bp']:.1f}"},
        {"Metric": "Actionable", "Base": "Yes" if bm["is_actionable"] else "No", "Stressed": "Yes" if sm["is_actionable"] else "No", "Delta": "--"},
    ]
    st.dataframe(summary_rows, use_container_width=True)

    # ---- Strategy verdict ----
    st.markdown("---")
    st.markdown("### Strategy Verdict")
    pickup_survives = sm["hedged_pickup_bp"] > 0
    still_actionable = sm["is_actionable"]
    if pickup_survives and still_actionable:
        st.success(
            "Strategy **survives** the stress scenario. Hedged pickup remains positive "
            "and the trade clears the friction band. Proceed with execution subject to "
            "operational constraints."
        )
    elif pickup_survives:
        st.warning(
            "Hedged pickup is positive but the trade no longer clears the friction band. "
            "The edge exists in theory but may not be executable at scale."
        )
    else:
        st.error(
            "Strategy **fails** under stress. Hedged pickup turns negative, meaning all "
            "carry is consumed by widened basis, higher frictions, or both."
        )

    learning_hint(
        "This dashboard consolidates every output from the seven lessons. "
        "Use it as a reference to see how a single scenario change flows through "
        "mechanics, parity, funding, frictions, and hedging. "
        "Try applying different scenarios from the sidebar to build intuition for how "
        "the pieces connect."
    )


if __name__ == "__main__":
    render_page()
else:
    render_page()
