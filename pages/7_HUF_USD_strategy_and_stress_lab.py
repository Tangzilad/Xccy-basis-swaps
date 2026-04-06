from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.conversion_factor import conversion_factor_from_fx
from src.analytics.conversion_factor import conversion_factor_curve_aware, translate_spread_bp
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.funding import all_in_funding_decomposition
from src.analytics.hedging import hedged_pickup_decomposition_bp, matched_vs_rolling_hedge_economics_bp
from src.analytics.parity import fair_value_comparison
from src.analytics.xccy_swap import synthetic_funding_cost_outputs
from src.explainers.theory_panels import render_pedagogical_scaffold
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "raw_basis_wedge",
    "synthetic_funding_cost",
    "friction_adjusted_arbitrage_band",
    "conversion_factor",
    "hedged_pickup",
    "stressed_vs_base_deltas",
)


def _compute_metrics(snapshot: dict) -> dict:
    usd_df = snapshot["usd_curve_df"].set_index("tenor")
    huf_df = snapshot["huf_curve_df"].set_index("tenor")
    basis_df = snapshot["basis_curve_df"].set_index("tenor")
    credit_df = snapshot["credit_assumptions"].set_index("tenor")
    friction_df = snapshot["friction_assumptions"].set_index("tenor")
    forward_df = snapshot["market_forward_df"].set_index("tenor")

    spot = float(snapshot["spot_fx"])
    usd = float(usd_df.loc["1Y", "usd_zero_rate"])
    huf = float(huf_df.loc["1Y", "huf_zero_rate"])
    bps = float(basis_df.loc["1Y", "basis_bps"])
    basis = bps / 10_000.0

    # Use observed market forward (not reconstructed from rates+basis)
    fwd = float(forward_df.loc["1Y", "market_forward"])
    parity = fair_value_comparison(spot, fwd, usd, huf, 1.0)

    fr = friction_adjusted_arbitrage_band_bp(
        parity["raw_basis_wedge_bp"],
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.6,
        float(friction_df.loc["1Y", "funding_friction_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]),
        float(credit_df.loc["1Y", "credit_spread_bps"]) * 0.4,
        3.0,
        8.0,
    )

    funding = all_in_funding_decomposition(
        domestic_curve_rate=huf,
        foreign_curve_rate=usd,
        basis_spread=basis,
        extra_spread=0.0012,
    )

    # 1Y conversion factor from observed forward, plus a curve-aware ladder CF.
    simple_cf = conversion_factor_from_fx(spot, fwd)
    ladder_forwards = [
        float(forward_df.loc[tenor, "market_forward"])
        for tenor in ("3M", "6M", "1Y", "2Y", "5Y")
        if tenor in forward_df.index
    ]
    ladder_years = [
        float(forward_df.loc[tenor, "years"])
        for tenor in ("3M", "6M", "1Y", "2Y", "5Y")
        if tenor in forward_df.index
    ]
    ladder_discount = [1.0 / (1.0 + usd * year) for year in ladder_years]
    curve_cf_payload = conversion_factor_curve_aware(
        spot_huf_per_usd=spot,
        forward_huf_per_usd_by_tenor=ladder_forwards,
        tenor_years=ladder_years,
        discount_factors=ladder_discount,
    )
    curve_cf = float(curve_cf_payload["conversion_factor"])

    gross_pickup_translated = translate_spread_bp((huf - usd) * 10_000.0, curve_cf)
    pickup = hedged_pickup_decomposition_bp(
        gross_pickup_translated,
        hedge_cost_bp=40.0,
        basis_drag_bp=abs(bps),
        extra_friction_bp=fr["total_friction_bp"] * 0.1,
    )

    hedge_choice = matched_vs_rolling_hedge_economics_bp(
        matched_hedge_cost_bp=40.0,
        expected_rolling_cost_bp=34.0,
        roll_risk_proxy_bp=max(8.0, fr["total_friction_bp"] * 0.15),
        risk_aversion_multiplier=0.6,
    )

    syn = synthetic_funding_cost_outputs(spot, fwd, huf, basis, 1.0)
    return {
        "spot": spot,
        "forward": fwd,
        "usd_rate": usd,
        "huf_rate": huf,
        "basis_bps": bps,
        "parity": parity,
        "funding": funding,
        "frictions": fr,
        "conversion_factor_simple": simple_cf,
        "conversion_factor_curve": curve_cf,
        "pickup": pickup,
        "hedge_choice": hedge_choice,
        "synthetic": syn,
    }


def render_page() -> None:

    st.set_page_config(page_title="7. HUF/USD strategy and stress lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[6]
    st.title("7. HUF/USD strategy and stress lab")
    render_pedagogical_scaffold(
        st,
        page_number=7,
        learning_path=LEARNING_PATH,
        quantitative_outputs=(
            "Base vs stressed CIP wedge",
            "Base vs stressed funding gap and friction-adjusted edge",
            "Base vs stressed hedged pickup",
            "Preferred hedge under stress",
        ),
        derivation_items=(
            ("State comparison construction", "Compute the same metric stack on base and stressed snapshots."),
            ("Stress delta extraction", "Report stressed minus base differences for decision variables."),
            ("Decision framing", "Use edge, pickup, and hedge preference jointly before committing capital."),
        ),
    )

    context = get_canonical_market_context(st.session_state)
    base_summary = context["summary_1y"]["base"]
    base_snapshot = context["base_snapshot"]
    stressed_snapshot = context["stressed_snapshot"]

    bm, sm = _compute_metrics(base_snapshot), _compute_metrics(stressed_snapshot)

    # --- Header with learning objectives ---
    render_page_header(6, "7. HUF/USD Strategy and Stress Lab")
    st.caption(f"Active scenario: **{context['state'].get('scenario', 'none')}**")
    st.caption(f"Canonical 1Y baseline: spot={base_summary['spot_fx']:.2f}, basis={base_summary['basis_bps']:.1f} bps")

    # --- Delta metrics ---
    st.markdown("### Stress Impact Summary")
    a, b, c, d = st.columns(4)
    a.metric("Basis (base)", f"{bm['basis_bps']:.1f} bps")
    b.metric("Basis (stressed)", f"{sm['basis_bps']:.1f} bps", delta=f"{sm['basis_bps'] - bm['basis_bps']:.1f}")
    c.metric(
        "Pickup (stressed)",
        f"{sm['pickup']['net_hedged_pickup_bp']:.1f} bps",
        delta=f"{sm['pickup']['net_hedged_pickup_bp'] - bm['pickup']['net_hedged_pickup_bp']:.1f}",
    )
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
                "Base": f"{bm['pickup']['net_hedged_pickup_bp']:.1f}",
                "Stressed": f"{sm['pickup']['net_hedged_pickup_bp']:.1f}",
                "Delta": f"{sm['pickup']['net_hedged_pickup_bp'] - bm['pickup']['net_hedged_pickup_bp']:.1f}",
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
        {
            "state": "Base",
            "Basis (bps)": bm["basis_bps"],
            "Pickup (bps)": bm["pickup"]["net_hedged_pickup_bp"],
            "Raw wedge (bps)": bm["parity"]["raw_basis_wedge_bp"],
        },
        {
            "state": "Stressed",
            "Basis (bps)": sm["basis_bps"],
            "Pickup (bps)": sm["pickup"]["net_hedged_pickup_bp"],
            "Raw wedge (bps)": sm["parity"]["raw_basis_wedge_bp"],
        },
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
    pickup_survives = sm["pickup"]["net_hedged_pickup_bp"] > 0
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
                title="Stressed raw wedge",
                meaning="Stress-scenario implied-minus-curve HUF wedge in basis points.",
                significance="Primary stress signal for parity dislocation severity.",
                formula=r"(r_{HUF}^{impl}-r_{HUF})\times10{,}000",
                methodology="Compute stress implied HUF rate and subtract stress curve HUF rate.",
                inputs="Stress spot, forward, and rates.",
                substituted_values=f"$S={sm['spot']:.4f}, F={sm['forward']:.4f}$",
                derivation_steps=("Compute stress implied HUF rate.", "Subtract stress HUF curve rate.", "Convert to bps.",),
                assumptions=("Positive wedge means richer implied HUF.",),
                interpretation="Higher positive wedge indicates stronger parity stress.",
                common_misunderstandings=("Reading stress wedge without consistent quote convention.",),
                result=f"{sm['parity']['raw_basis_wedge_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Stressed net edge",
                meaning="Stress-scenario residual edge after friction costs.",
                significance="Determines if dislocation remains executable in stress.",
                formula=r"\text{Raw edge}-\text{Friction}",
                methodology="Subtract stressed friction estimate from stressed raw edge.",
                inputs="Stressed raw edge and stressed friction (bps).",
                substituted_values=f"${sm['frictions']['raw_edge_bp']:.2f}-{sm['frictions']['total_friction_bp']:.2f}$",
                derivation_steps=("Measure stressed raw edge.", "Subtract stressed friction.",),
                assumptions=("Costs reduce tradeability.",),
                interpretation="Positive net edge suggests stressed trade may remain viable.",
                common_misunderstandings=("Ignoring friction escalation in stress.",),
                result=f"{sm['frictions']['net_edge_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Stressed hedged pickup",
                meaning="Stress net hedged carry after all implementation deductions.",
                significance="Bottom-line strategy viability metric under adverse conditions.",
                formula=r"\text{Gross}-\text{hedge}-\text{basis}-\text{extra}",
                methodology="Apply decomposition with stressed conversion factor and costs.",
                inputs="Stressed CF, basis drag, hedge cost, and extra friction.",
                substituted_values=f"$CF={sm['conversion_factor_curve']:.6f}, basis={abs(sm['basis_bps']):.2f}$",
                derivation_steps=("Compute stressed gross pickup.", "Subtract hedge/basis/friction drags.",),
                assumptions=("Positive pickup remains attractive.",),
                interpretation="Positive stressed pickup indicates resilient strategy economics.",
                common_misunderstandings=("Comparing stressed pickup directly to unstressed baseline without attribution.",),
                result=f"{sm['pickup']['net_hedged_pickup_bp']:.2f} bps",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(6)


if __name__ == "__main__":
    render_page()
else:
    render_page()
