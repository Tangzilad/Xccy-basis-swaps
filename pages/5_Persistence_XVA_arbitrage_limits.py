from __future__ import annotations

from src.explainers.theory_panels import render_pedagogical_scaffold
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.state.session_access import get_canonical_market_context


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="5. Persistence / XVA / arbitrage limits", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[4]
    st.title("5. Persistence / XVA / arbitrage limits")
    render_pedagogical_scaffold(
        st,
        page_number=5,
        learning_path=LEARNING_PATH,
        quantitative_outputs=(
            "Raw edge (bp)",
            "Total friction band (bp)",
            "Net edge by capacity multiplier",
            "Actionability flag",
        ),
        derivation_items=(
            ("Total friction stack", "Sum capital, funding, CVA/FVA, clearing, and liquidity frictions."),
            ("Net edge", "Subtract friction band from raw wedge signal to get executable edge."),
            ("Actionability test", "Check whether absolute raw edge exceeds friction threshold."),
        ),
    )

    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
    raw = abs(float(summary["basis_bps"]))
    capital_charge_bp, funding_spread_bp, cva_proxy_bp = 9.0, 6.0, 4.0
    fva_proxy_bp, clearing_friction_bp, liquidity_repo_friction_bp = 3.0, 2.0, 5.0

    rows = []
    for cap in [0.8, 1.0, 1.2, 1.5]:
        rows.append(
            {
                "capacity": cap,
                **friction_adjusted_arbitrage_band_bp(
                    raw,
                    capital_charge_bp,
                    funding_spread_bp,
                    cva_proxy_bp,
                    fva_proxy_bp,
                    clearing_friction_bp,
                    liquidity_repo_friction_bp,
                    1.0,
                    cap,
                ),
            }
        )
    base = next(r for r in rows if r["capacity"] == 1.0)

    a, b, c = st.columns(3)
    a.metric("Raw edge", f"{base['raw_edge_bp']:.2f} bps")
    b.metric("Friction", f"{base['total_friction_bp']:.2f} bps")
    c.metric("Actionable", "Yes" if base["is_actionable"] else "No")
    st.line_chart({"capacity": [r['capacity'] for r in rows], "net": [r['net_edge_bp'] for r in rows], "band": [r['upper_band_bp'] for r in rows]}, x="capacity")
    st.dataframe(rows, use_container_width=True)
    st.write("If the raw edge stays within the friction band, dislocations can persist.")
    learning_hint("Capacity and XVA multipliers control when arbitrage is truly executable.")
    render_calculation_windows([
        CalculationWindow(
            title="Total friction",
            concept_meaning="Aggregate implementation drag from capital, funding, XVA, and liquidity costs.",
            why_it_matters="Defines the no-trade band around raw apparent arbitrage.",
            formula=r"(\sum c_i)\times m_{cp}\times m_{cap}",
            methodology_rationale="Sum individual friction components, then scale by multipliers.",
            inputs_used="All friction components in bps, plus counterparty/capacity multipliers.",
            substituted_values=f"$({capital_charge_bp}+{funding_spread_bp}+{cva_proxy_bp}+{fva_proxy_bp}+{clearing_friction_bp}+{liquidity_repo_friction_bp})$",
            derivation_steps=("Sum component frictions.", "Apply multipliers.",),
            assumptions=("Components are additive proxies.",),
            interpretation="Higher friction widens persistence band.",
            common_misunderstandings=("Comparing raw edges without netting implementation costs.",),
            result=f"{base['total_friction_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Net edge",
            concept_meaning="Residual tradable edge after friction deduction.",
            why_it_matters="Determines whether dislocation is economically exploitable.",
            formula=r"\text{Raw edge}-\text{Friction}",
            methodology_rationale="Subtract total friction from observed raw edge.",
            inputs_used="Raw edge and total friction in bps.",
            substituted_values=f"${base['raw_edge_bp']:.2f}-{base['total_friction_bp']:.2f}$",
            derivation_steps=("Measure raw edge.", "Subtract friction estimate.",),
            assumptions=("Friction estimate is contemporaneously valid.",),
            interpretation="Positive net edge implies residual arbitrage value.",
            common_misunderstandings=("Using absolute raw edge instead of net value for trade decisions.",),
            result=f"{base['net_edge_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Actionability",
            concept_meaning="Binary executable-trade check against the friction band.",
            why_it_matters="Converts valuation signal into operational decision criterion.",
            formula=r"|\text{Raw edge}|>\text{Friction}",
            methodology_rationale="Trade only when edge magnitude clears the cost band.",
            inputs_used="Absolute raw edge and total friction, both in bps.",
            substituted_values=f"$|{base['raw_edge_bp']:.2f}|>{base['total_friction_bp']:.2f}$",
            derivation_steps=("Take absolute raw edge.", "Compare to friction threshold.",),
            assumptions=("Execution can occur at modeled costs.",),
            interpretation="True means edge is large enough to consider trading.",
            common_misunderstandings=("Treating a positive raw edge as automatically actionable.",),
            result="Actionable" if base["is_actionable"] else "Not actionable",
        ),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
