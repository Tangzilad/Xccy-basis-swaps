from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


def render_page() -> None:
    st.set_page_config(page_title="5. Persistence / XVA / arbitrage limits", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[4]

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
                "Total friction",
                r"(\sum c_i)\times m_{cp}\times m_{cap}",
                f"$({capital_charge_bp}+{funding_spread_bp}+{cva_proxy_bp}+{fva_proxy_bp}+{clearing_friction_bp}+{liquidity_repo_friction_bp})\\times 1.0 \\times 1.0$",
                ("All friction terms are additive costs.",),
                assumptions=(
                    "Counterparty quality multiplier = 1.0 (neutral).",
                    "Capacity multiplier scales the entire friction band.",
                ),
                result=f"{base['total_friction_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Net edge",
                r"\text{Net edge}=\text{Raw edge}-\text{Total friction}",
                f"${base['raw_edge_bp']:.2f}-{base['total_friction_bp']:.2f}$",
                ("Positive net edge implies residual arbitrage value after costs.",),
                result=f"{base['net_edge_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Actionability test",
                r"|\text{Raw edge}|>\text{Total friction}",
                f"$|{base['raw_edge_bp']:.2f}|>{base['total_friction_bp']:.2f}$",
                ("Trade must clear the friction band to be executable.",),
                result="Actionable" if base["is_actionable"] else "Not actionable",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(4)


if __name__ == "__main__":
    render_page()
else:
    render_page()
