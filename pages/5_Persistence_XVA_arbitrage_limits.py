from __future__ import annotations

import pandas as pd

from src.analytics.frictions import (
    friction_adjusted_arbitrage_band_bp,
    friction_components_bp,
)


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {
        "basis_bps": -22.0,
        "capital_charge_bp": 9.0,
        "funding_spread_bp": 6.0,
        "cva_proxy_bp": 4.0,
        "fva_proxy_bp": 3.0,
        "clearing_friction_bp": 2.0,
        "liquidity_repo_friction_bp": 5.0,
        "counterparty_quality_multiplier": 1.0,
        "capacity_multiplier": 1.0,
    }
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="5. Persistence / XVA / arbitrage limits", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[4]
    m = _get_market_state(st.session_state)

    st.title("5. Persistence / XVA / arbitrage limits")
    st.caption("Deterministic friction aggregation (no random sampling in this path).")

    st.subheader("Inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        raw_edge_bp = st.number_input("Raw edge (bp)", value=float(m.get("basis_bps", -22.0)), step=0.5)
        capital_charge_bp = st.number_input("Capital (bp)", min_value=0.0, value=float(m["capital_charge_bp"]), step=0.5)
        funding_spread_bp = st.number_input("Funding (bp)", min_value=0.0, value=float(m["funding_spread_bp"]), step=0.5)
    with c2:
        cva_proxy_bp = st.number_input("CVA (bp)", min_value=0.0, value=float(m["cva_proxy_bp"]), step=0.5)
        fva_proxy_bp = st.number_input("FVA (bp)", min_value=0.0, value=float(m["fva_proxy_bp"]), step=0.5)
        clearing_friction_bp = st.number_input("Clearing (bp)", min_value=0.0, value=float(m["clearing_friction_bp"]), step=0.5)
    with c3:
        liquidity_repo_friction_bp = st.number_input(
            "Liquidity / repo (bp)", min_value=0.0, value=float(m["liquidity_repo_friction_bp"]), step=0.5
        )
        counterparty_quality_multiplier = st.number_input(
            "Counterparty multiplier", min_value=0.1, value=float(m.get("counterparty_quality_multiplier", 1.0)), step=0.05
        )
        capacity_multiplier = st.number_input(
            "Capacity multiplier", min_value=0.1, value=float(m.get("capacity_multiplier", 1.0)), step=0.05
        )

    # persist deterministic input state
    m.update(
        {
            "basis_bps": raw_edge_bp,
            "capital_charge_bp": capital_charge_bp,
            "funding_spread_bp": funding_spread_bp,
            "cva_proxy_bp": cva_proxy_bp,
            "fva_proxy_bp": fva_proxy_bp,
            "clearing_friction_bp": clearing_friction_bp,
            "liquidity_repo_friction_bp": liquidity_repo_friction_bp,
            "counterparty_quality_multiplier": counterparty_quality_multiplier,
            "capacity_multiplier": capacity_multiplier,
        }
    )

    base = friction_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=raw_edge_bp,
        capital_charge_bp=capital_charge_bp,
        funding_spread_bp=funding_spread_bp,
        cva_proxy_bp=cva_proxy_bp,
        fva_proxy_bp=fva_proxy_bp,
        clearing_friction_bp=clearing_friction_bp,
        liquidity_repo_friction_bp=liquidity_repo_friction_bp,
        counterparty_quality_multiplier=counterparty_quality_multiplier,
        capacity_multiplier=capacity_multiplier,
    )

    st.subheader("Outputs")
    a, b, c, d = st.columns(4)
    a.metric("Total friction", f"{base['total_friction_bp']:.2f} bps")
    b.metric("Band [lower, upper]", f"[{base['lower_band_bp']:.2f}, {base['upper_band_bp']:.2f}] bps")
    c.metric("Net edge", f"{base['net_edge_bp']:.2f} bps")
    d.metric("Actionable", "Yes" if base["is_actionable"] else "No")

    if base["sign_case"] == "positive_raw_edge":
        st.info("Sign convention: raw edge > 0, so net edge = raw edge - friction.")
    elif base["sign_case"] == "negative_raw_edge":
        st.info("Sign convention: raw edge < 0, so net edge = raw edge + friction.")
    else:
        st.info("Sign convention: raw edge = 0, so net edge is 0 and cannot be actionable.")

    st.subheader("Visuals")

    # 1) net edge vs capacity
    capacity_grid = [round(x, 2) for x in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]]
    cap_rows = []
    for cap_mult in capacity_grid:
        r = friction_adjusted_arbitrage_band_bp(
            raw_basis_edge_bp=raw_edge_bp,
            capital_charge_bp=capital_charge_bp,
            funding_spread_bp=funding_spread_bp,
            cva_proxy_bp=cva_proxy_bp,
            fva_proxy_bp=fva_proxy_bp,
            clearing_friction_bp=clearing_friction_bp,
            liquidity_repo_friction_bp=liquidity_repo_friction_bp,
            counterparty_quality_multiplier=counterparty_quality_multiplier,
            capacity_multiplier=cap_mult,
        )
        cap_rows.append({"capacity_multiplier": cap_mult, "net_edge_bp": r["net_edge_bp"]})
    cap_df = pd.DataFrame(cap_rows).set_index("capacity_multiplier")
    st.write("Net edge vs capacity")
    st.line_chart(cap_df)

    # 2) raw edge vs friction band
    band_df = pd.DataFrame(
        [
            {"series": "raw_edge_bp", "value_bp": base["raw_edge_bp"]},
            {"series": "upper_band_bp", "value_bp": base["upper_band_bp"]},
            {"series": "lower_band_bp", "value_bp": base["lower_band_bp"]},
        ]
    ).set_index("series")
    st.write("Raw edge vs friction band")
    st.bar_chart(band_df)

    # 3) capital/liquidity stress sensitivity
    stress_rows = []
    for stress in [0.75, 1.0, 1.25, 1.5]:
        stress_result = friction_adjusted_arbitrage_band_bp(
            raw_basis_edge_bp=raw_edge_bp,
            capital_charge_bp=capital_charge_bp * stress,
            funding_spread_bp=funding_spread_bp,
            cva_proxy_bp=cva_proxy_bp,
            fva_proxy_bp=fva_proxy_bp,
            clearing_friction_bp=clearing_friction_bp,
            liquidity_repo_friction_bp=liquidity_repo_friction_bp * stress,
            counterparty_quality_multiplier=counterparty_quality_multiplier,
            capacity_multiplier=capacity_multiplier,
        )
        stress_rows.append(
            {
                "stress_factor": stress,
                "total_friction_bp": stress_result["total_friction_bp"],
                "net_edge_bp": stress_result["net_edge_bp"],
            }
        )
    stress_df = pd.DataFrame(stress_rows).set_index("stress_factor")
    st.write("Capital/liquidity stress sensitivity")
    st.line_chart(stress_df)

    components = friction_components_bp(
        capital_charge_bp=capital_charge_bp,
        funding_spread_bp=funding_spread_bp,
        cva_proxy_bp=cva_proxy_bp,
        fva_proxy_bp=fva_proxy_bp,
        clearing_friction_bp=clearing_friction_bp,
        liquidity_repo_friction_bp=liquidity_repo_friction_bp,
    )

    st.subheader("Calculation windows")
    render_calculation_windows(
        [
            CalculationWindow(
                "Friction aggregation window",
                r"(Cap + Fund + CVA + FVA + Clear + Liq) \times m_{cp} \times m_{cap}",
                (
                    f"$({components['capital_charge_bp']:.2f}+{components['funding_spread_bp']:.2f}+"
                    f"{components['cva_proxy_bp']:.2f}+{components['fva_proxy_bp']:.2f}+"
                    f"{components['clearing_friction_bp']:.2f}+{components['liquidity_repo_friction_bp']:.2f})"
                    f"\\times {counterparty_quality_multiplier:.2f}\\times {capacity_multiplier:.2f}$"
                ),
                (
                    "All friction terms are non-negative costs.",
                    "Counterparty and capacity multipliers scale total implementation drag.",
                ),
                result=f"{base['total_friction_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Actionable condition window",
                r"|Raw\ edge| > Friction",
                f"$|{base['raw_edge_bp']:.2f}| > {base['total_friction_bp']:.2f}$",
                (
                    "If true, dislocation clears the no-arbitrage friction band.",
                    "If false, basis can persist inside [lower, upper] friction bounds.",
                ),
                result="Actionable" if base["is_actionable"] else "Not actionable",
            ),
        ]
    )

    learning_hint("Capacity, liquidity and XVA frictions can keep apparent edges untradeable.")
