from __future__ import annotations

from src.analytics.frictions import friction_adjusted_arbitrage_band_bp


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {"basis_bps": float(session_state.get("cross_currency_basis_bps", -22)), "capital_charge_bp": 9.0, "funding_spread_bp": 6.0, "cva_proxy_bp": 4.0, "fva_proxy_bp": 3.0, "clearing_friction_bp": 2.0, "liquidity_repo_friction_bp": 5.0}
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="5. Persistence / XVA / arbitrage limits", page_icon="📘", layout="wide")
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[4]
    m = _get_market_state(st.session_state)
    raw = abs(float(m["basis_bps"]))
    rows=[]
    for cap in [0.8,1.0,1.2,1.5]:
        rows.append({"capacity":cap, **friction_adjusted_arbitrage_band_bp(raw, m["capital_charge_bp"], m["funding_spread_bp"], m["cva_proxy_bp"], m["fva_proxy_bp"], m["clearing_friction_bp"], m["liquidity_repo_friction_bp"], 1.0, cap)})
    base=next(r for r in rows if r["capacity"]==1.0)
    st.title("5. Persistence / XVA / arbitrage limits")
    a,b,c=st.columns(3); a.metric("Raw edge",f"{base['raw_edge_bp']:.2f} bps"); b.metric("Friction",f"{base['total_friction_bp']:.2f} bps"); c.metric("Actionable", "Yes" if base["is_actionable"] else "No")
    st.line_chart({"capacity":[r['capacity'] for r in rows], "net":[r['net_edge_bp'] for r in rows], "band":[r['upper_band_bp'] for r in rows]}, x="capacity")
    st.dataframe(rows,use_container_width=True)
    st.write("If the raw edge stays within the friction band, dislocations can persist.")
    learning_hint("Capacity and XVA multipliers control when arbitrage is truly executable.")
    render_calculation_windows([
        CalculationWindow("Total friction", r"(\sum c_i)\times m_{cp}\times m_{cap}", f"$({m['capital_charge_bp']}+{m['funding_spread_bp']}+{m['cva_proxy_bp']}+{m['fva_proxy_bp']}+{m['clearing_friction_bp']}+{m['liquidity_repo_friction_bp']})$", ("All friction terms are costs.",), result=f"{base['total_friction_bp']:.2f} bps"),
        CalculationWindow("Net edge", r"\text{Raw edge}-\text{Friction}", f"${base['raw_edge_bp']:.2f}-{base['total_friction_bp']:.2f}$", ("Positive net edge implies residual arbitrage value.",), result=f"{base['net_edge_bp']:.2f} bps"),
        CalculationWindow("Actionability", r"|\text{Raw edge}|>\text{Friction}", f"$|{base['raw_edge_bp']:.2f}|>{base['total_friction_bp']:.2f}$", ("Must clear band to trade.",), result="Actionable" if base["is_actionable"] else "Not actionable"),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
