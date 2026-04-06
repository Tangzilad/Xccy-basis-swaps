from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.conversion_factor import conversion_factor_from_fx
from src.analytics.conversion_factor import conversion_factor_curve_aware, conversion_factor_from_fx, translate_spread_bp
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
    import streamlit as st
    from streamlit_calc_helpers import (
        CalculationWindow,
        SignConventionContext,
        render_calculation_windows,
        render_shared_sign_convention,
    )
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

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
            "state": "base",
            "cip_wedge_bp": bm["parity"]["raw_basis_wedge_bp"],
            "funding_gap_bp": bm["funding"]["cross_market_gap"] * 10_000.0,
            "friction_adjusted_edge_bp": bm["frictions"]["net_edge_bp"],
            "conversion_factor": bm["conversion_factor_curve"],
            "hedged_pickup_bp": bm["pickup"]["net_hedged_pickup_bp"],
            "preferred_hedge": bm["hedge_choice"]["preferred_hedge"],
        },
        {
            "state": "stressed",
            "cip_wedge_bp": sm["parity"]["raw_basis_wedge_bp"],
            "funding_gap_bp": sm["funding"]["cross_market_gap"] * 10_000.0,
            "friction_adjusted_edge_bp": sm["frictions"]["net_edge_bp"],
            "conversion_factor": sm["conversion_factor_curve"],
            "hedged_pickup_bp": sm["pickup"]["net_hedged_pickup_bp"],
            "preferred_hedge": sm["hedge_choice"]["preferred_hedge"],
        },
    ]

    st.caption(f"Scenario: {context['state'].get('scenario', 'none')}")
    a, b, c = st.columns(3)
    a.metric("Δ CIP wedge", f"{sm['parity']['raw_basis_wedge_bp'] - bm['parity']['raw_basis_wedge_bp']:.2f} bps")
    b.metric("Δ hedged pickup", f"{sm['pickup']['net_hedged_pickup_bp'] - bm['pickup']['net_hedged_pickup_bp']:.2f} bps")
    c.metric("Stress preferred hedge", str(sm["hedge_choice"]["preferred_hedge"]).title())

    st.bar_chart(
        {
            "state": [r["state"] for r in rows],
            "cip_wedge_bp": [r["cip_wedge_bp"] for r in rows],
            "friction_adjusted_edge_bp": [r["friction_adjusted_edge_bp"] for r in rows],
            "hedged_pickup_bp": [r["hedged_pickup_bp"] for r in rows],
        },
        x="state",
    )
    st.dataframe(rows, use_container_width=True)
    st.write("Stress scenarios roll into CIP wedge, funding transformation, frictions, and hedge economics.")
    learning_hint("Check whether net pickup survives widened friction bands and whether hedge preference flips.")
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Strategy desk compares base vs stressed state across parity, funding, frictions, and hedging.",
        positive_interpretation="Positive delta/edge/pickup supports the shown trade direction in the current scenario.",
        negative_interpretation="Negative delta/edge/pickup favors reducing risk or taking the opposite direction.",
    )
    render_shared_sign_convention(sign_context)

    render_calculation_windows([
        CalculationWindow(
            title="Stressed CIP wedge",
            concept_meaning="Parity wedge under stressed market forward and rates.",
            why_it_matters="Primary stress indicator for cross-currency dislocation.",
            formula=r"(r_{HUF}^{impl}-r_{HUF})\times10{,}000",
            methodology_rationale="Recover implied HUF funding from stressed spot-forward parity.",
            inputs_used="Stressed spot, stressed observed forward, stressed rates, 1Y tenor.",
            substituted_values=f"$S={sm['spot']:.4f}, F_{{mkt,1Y}}={sm['forward']:.4f}$",
            derivation_steps=("Compute implied HUF rate from stressed parity.", "Subtract stressed curve HUF rate.", "Convert to bps.",),
            assumptions=("Observed forward reflects executable stressed market conditions.",),
            interpretation="Larger absolute wedge indicates stronger parity stress.",
            common_misunderstandings=("Using model forward instead of stressed observed forward.",),
            result=f"{sm['parity']['raw_basis_wedge_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Stressed funding transformation",
            concept_meaning="Stress-state funding route comparison for domestic currency.",
            why_it_matters="Identifies whether route preference flips under stress.",
            formula=r"\Delta r = r_{syn,dom} - r_{dir,dom}",
            methodology_rationale="Compare synthetic and direct all-in funding in stressed state.",
            inputs_used="Stressed synthetic and direct all-in domestic rates.",
            substituted_values=f"${sm['funding']['synthetic_all_in']:.6f}-{sm['funding']['domestic_all_in']:.6f}$",
            derivation_steps=("Build stressed synthetic all-in rate.", "Build stressed domestic all-in rate.", "Take difference.",),
            assumptions=("Both routes share comparable maturity and compounding.",),
            interpretation="Positive means synthetic HUF funding is less economical than direct.",
            common_misunderstandings=("Assuming base-state ranking survives stress unchanged.",),
            result=f"{sm['funding']['cross_market_gap'] * 10_000:.2f} bps",
        ),
        CalculationWindow(
            title="Stressed friction-adjusted edge",
            concept_meaning="Residual stressed dislocation after implementation frictions.",
            why_it_matters="Separates visible dislocation from executable opportunity.",
            formula=r"\text{CIP wedge}-\text{Friction}",
            methodology_rationale="Net raw stressed edge by stressed friction band estimate.",
            inputs_used="Stressed raw edge and total friction in bps.",
            substituted_values=f"${sm['frictions']['raw_edge_bp']:.2f}-{sm['frictions']['total_friction_bp']:.2f}$",
            derivation_steps=("Measure stressed raw edge.", "Estimate stressed friction total.", "Subtract to obtain net edge.",),
            assumptions=("Friction proxies remain informative in stress.",),
            interpretation="Actionable only if absolute wedge exceeds friction band.",
            common_misunderstandings=("Acting on raw edge without friction adjustment.",),
            result=f"{sm['frictions']['net_edge_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Stressed conversion factor",
            concept_meaning="Stress-state conversion mapping between quote spaces.",
            why_it_matters="Impacts translated pickup and hedge metrics under stress.",
            formula=r"CF_{curve}=\sum_i w_i(F_i/S)",
            methodology_rationale="Recompute weighted forward/spot mapping with stressed ladder.",
            inputs_used="Stressed spot, forward ladder, and tenor weights.",
            substituted_values=f"$CF_{{simple}}={sm['conversion_factor_simple']:.6f},\\;CF_{{curve}}={sm['conversion_factor_curve']:.6f}$",
            derivation_steps=("Compute stressed simple CF.", "Compute stressed curve-aware CF.", "Compare translation implications.",),
            assumptions=("Weights remain representative for stressed hedging horizon.",),
            interpretation="Gap versus simple CF shows curve-shape stress contribution.",
            common_misunderstandings=("Treating CF as invariant across scenarios.",),
            result=f"{sm['conversion_factor_curve']:.6f}",
        ),
        CalculationWindow(
            title="Stressed hedged pickup",
            concept_meaning="Net stressed carry after hedging and friction costs.",
            why_it_matters="Directly indicates strategy attractiveness in stress.",
            formula=r"\text{Net}=\text{Gross}-\text{Hedge}-\text{Basis}-\text{Extra}",
            methodology_rationale="Subtract each stressed cost channel from stressed gross pickup.",
            inputs_used="Stressed gross pickup, hedge cost, basis drag, extra friction (bps).",
            substituted_values=f"${sm['pickup']['gross_pickup_bp']:.2f}-{sm['pickup']['hedge_cost_bp']:.2f}-{sm['pickup']['basis_drag_bp']:.2f}-{sm['pickup']['extra_friction_bp']:.2f}$",
            derivation_steps=("Start with stressed gross pickup.", "Subtract stressed hedge+basis terms.", "Subtract extra frictions.",),
            assumptions=("Additive bps decomposition is valid under stress magnitude.",),
            interpretation="Positive pickup remains attractive after implementation costs.",
            common_misunderstandings=("Reading gross pickup without stress cost channels.",),
            result=f"{sm['pickup']['net_hedged_pickup_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Stressed preferred hedge choice",
            concept_meaning="Stress-state decision between matched and rolling hedge implementation.",
            why_it_matters="Hedge preference can flip under volatility and spread shocks.",
            formula=r"\text{choose rolling if } C_m-(C_r+\lambda\sigma)>0",
            methodology_rationale="Compare matched cost with risk-adjusted rolling cost.",
            inputs_used="Stressed matched cost, expected rolling cost, roll-risk proxy, risk aversion.",
            substituted_values=f"$C_m={sm['hedge_choice']['matched_cost_bp']:.2f}, C_r={sm['hedge_choice']['expected_rolling_cost_bp']:.2f}, \\sigma={sm['hedge_choice']['roll_risk_proxy_bp']:.2f}$",
            derivation_steps=("Compute RA rolling cost C_r+λσ.", "Compare with matched cost C_m.", "Choose lower risk-adjusted option.",),
            assumptions=("Risk-aversion setting reflects mandate.",),
            interpretation="Choice summarizes stress-adjusted implementation preference.",
            common_misunderstandings=("Selecting lowest expected cost without risk adjustment.",),
            result=f"{str(sm['hedge_choice']['preferred_hedge']).title()}",
        ),
    ], sign_convention=sign_context)

    st.subheader("Scenario conclusion prompts")
    st.markdown("- What changed?\n- Why it changed?\n- Would I still do the trade?")
    if hasattr(st, "text_area"):
        st.text_area("What changed?", key="stress_conclusion_what_changed", height=90)
        st.text_area("Why it changed?", key="stress_conclusion_why_changed", height=90)
        st.text_area("Would I still do the trade?", key="stress_conclusion_do_trade", height=90)


if __name__ == "__main__":
    render_page()
else:
    render_page()
