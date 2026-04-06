from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


from src.explainers.theory_panels import render_pedagogical_scaffold

REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "friction_adjusted_arbitrage_band",
    "forward_difference",
    "raw_basis_wedge",
)


def render_page() -> None:
    from streamlit_calc_helpers import (
        SignConventionContext,
        render_shared_sign_convention,
    )

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
    raw = float(summary["basis_bps"])
    capital_charge_bp, funding_spread_bp, cva_proxy_bp = 9.0, 6.0, 4.0
    fva_proxy_bp, clearing_friction_bp, liquidity_repo_friction_bp = 3.0, 2.0, 5.0

    rows = []
    for cap in [0.8, 1.0, 1.2, 1.5]:
        rows.append(
            {
                "capacity": cap,
                **friction_adjusted_arbitrage_band_bp(
                    raw, capital_charge_bp, funding_spread_bp, cva_proxy_bp,
                    fva_proxy_bp, clearing_friction_bp, liquidity_repo_friction_bp,
                    1.0, cap,
                ),
            }
        )
    base = next(r for r in rows if r["capacity"] == 1.0)

    # --- Header with learning objectives ---
    render_page_header(4, "5. Persistence / XVA / Arbitrage Limits")

    # --- Metrics ---
    a, b, c = st.columns(3)
    a.metric("Raw edge", f"{base['raw_edge_bp']:.2f} bps")
    b.metric("Total friction", f"{base['total_friction_bp']:.2f} bps")
    c.metric("Actionable", "Yes" if base["is_actionable"] else "No")

    # --- Chart ---
    st.markdown("### Net Edge vs Friction Band Across Capacity")
    st.line_chart(
        {
            "capacity": [r["capacity"] for r in rows],
            "net_edge": [r["net_edge_bp"] for r in rows],
            "friction_band": [r["upper_band_bp"] for r in rows],
        },
        x="capacity",
    )
    st.dataframe(rows, use_container_width=True)

    # --- Friction breakdown ---
    st.markdown("### Friction Component Breakdown")
    friction_data = {
        "Component": ["Capital charge", "Funding spread", "CVA proxy", "FVA proxy", "Clearing", "Liquidity/repo"],
        "bps": [capital_charge_bp, funding_spread_bp, cva_proxy_bp, fva_proxy_bp, clearing_friction_bp, liquidity_repo_friction_bp],
    }
    st.bar_chart(friction_data, x="Component", y="bps")

    st.markdown(
        "If the raw edge stays within the friction band, the dislocation persists because "
        "no market participant can profitably exploit it after accounting for all costs."
    )

    learning_hint(
        "This is the key insight of the persistence puzzle: basis dislocations are not 'free money'. "
        "Each friction component represents a real cost. Capital charges alone often consume half "
        "the available edge. Try increasing the capacity multiplier to see how constrained balance "
        "sheets make more trades unactionable."
    )

    # --- Calculation windows ---
    render_calculation_windows(
        [
            CalculationWindow(
                title="Total friction",
                meaning="Aggregate implementation drag from capital, funding, XVA, and liquidity components.",
                significance="Defines the no-trade band around apparent raw arbitrage.",
                formula=r"(\sum c_i)\times m_{cp}\times m_{cap}",
                methodology="Sum friction components and apply counterparty/capacity multipliers.",
                inputs="Capital, funding, CVA, FVA, clearing, and liquidity frictions with multipliers.",
                substituted_values=f"$({capital_charge_bp}+{funding_spread_bp}+{cva_proxy_bp}+{fva_proxy_bp}+{clearing_friction_bp}+{liquidity_repo_friction_bp})\\times 1.0 \\times 1.0$",
                derivation_steps=("Add friction components.", "Apply multipliers m_cp and m_cap.",),
                assumptions=(
                    "All friction terms are additive costs.",
                    "Counterparty quality multiplier = 1.0 (neutral).",
                    "Capacity multiplier scales the entire friction band.",
                ),
                interpretation="Higher total friction widens the persistence band.",
                common_misunderstandings=("Comparing raw dislocations without cost netting.",),
                result=f"{base['total_friction_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Net edge",
                meaning="Residual tradable edge after subtracting total friction.",
                significance="Primary indicator of whether a dislocation remains exploitable.",
                formula=r"\text{Net edge}=\text{Raw edge}-\text{Total friction}",
                methodology="Deduct modeled friction from observed raw edge.",
                inputs="Raw edge and total friction (bps).",
                substituted_values=f"${base['raw_edge_bp']:.2f}-{base['total_friction_bp']:.2f}$",
                derivation_steps=("Measure raw edge.", "Subtract total friction.",),
                assumptions=("Positive net edge implies residual arbitrage value after costs.",),
                interpretation="Positive result indicates tradable residual edge.",
                common_misunderstandings=("Treating any positive raw edge as tradable.",),
                result=f"{base['net_edge_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Actionability test",
                meaning="Binary executable-trade check against the total friction threshold.",
                significance="Transforms valuation signal into an operational go/no-go decision.",
                formula=r"|\text{Raw edge}|>\text{Total friction}",
                methodology="Compare absolute raw edge with total friction band.",
                inputs="Raw edge and total friction (bps).",
                substituted_values=f"$|{base['raw_edge_bp']:.2f}|>{base['total_friction_bp']:.2f}$",
                derivation_steps=("Take absolute raw edge.", "Compare against friction threshold.",),
                assumptions=("Trade must clear the friction band to be executable.",),
                interpretation="True/Actionable means edge magnitude exceeds modeled costs.",
                common_misunderstandings=("Ignoring absolute value in direction-agnostic threshold checks.",),
                result="Actionable" if base["is_actionable"] else "Not actionable",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(4)
    st.write("If the raw edge stays within the friction band, dislocations can persist.")
    learning_hint("Capacity and XVA multipliers control when arbitrage is truly executable.")
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Arbitrageur evaluating direction-specific basis wedge after XVA/friction costs.",
        positive_interpretation="Positive raw/net edge favors trading in the quoted direction.",
        negative_interpretation="Negative raw/net edge favors the mirror trade direction.",
    )
    render_shared_sign_convention(sign_context)
    render_calculation_windows([
        CalculationWindow(
            title="Total friction",
            meaning="Aggregate implementation drag from capital, funding, XVA, and liquidity costs.",
            significance="Defines the no-trade band around raw apparent arbitrage.",
            formula=r"(\sum c_i)\times m_{cp}\times m_{cap}",
            methodology="Sum individual friction components, then scale by multipliers.",
            inputs="All friction components in bps, plus counterparty/capacity multipliers.",
            substituted_values=f"$({capital_charge_bp}+{funding_spread_bp}+{cva_proxy_bp}+{fva_proxy_bp}+{clearing_friction_bp}+{liquidity_repo_friction_bp})$",
            derivation_steps=("Sum component frictions.", "Apply multipliers.",),
            assumptions=("Components are additive proxies.",),
            interpretation="Higher friction widens persistence band.",
            common_misunderstandings=("Comparing raw edges without netting implementation costs.",),
            result=f"{base['total_friction_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Net edge",
            meaning="Residual tradable edge after friction deduction.",
            significance="Determines whether dislocation is economically exploitable.",
            formula=r"\text{Raw edge}-\text{Friction}",
            methodology="Subtract total friction from observed raw edge.",
            inputs="Raw edge and total friction in bps.",
            substituted_values=f"${base['raw_edge_bp']:.2f}-{base['total_friction_bp']:.2f}$",
            derivation_steps=("Measure raw edge.", "Subtract friction estimate.",),
            assumptions=("Friction estimate is contemporaneously valid.",),
            interpretation="Positive net edge implies residual arbitrage value.",
            common_misunderstandings=("Using absolute raw edge instead of net value for trade decisions.",),
            result=f"{base['net_edge_bp']:.2f} bps",
        ),
        CalculationWindow(
            title="Actionability",
            meaning="Binary executable-trade check against the friction band.",
            significance="Converts valuation signal into operational decision criterion.",
            formula=r"|\text{Raw edge}|>\text{Friction}",
            methodology="Trade only when edge magnitude clears the cost band.",
            inputs="Absolute raw edge and total friction, both in bps.",
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
