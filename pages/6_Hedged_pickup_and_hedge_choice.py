from __future__ import annotations

from src.analytics.conversion_factor import conversion_factor_from_fx, translate_spread_bp
from src.analytics.hedging import hedged_pickup_bp, matched_vs_rolling_hedge_economics_bp, roll_cost_and_risk_proxy_bp


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {"spot_fx": float(session_state.get("spot_fx", 1.08)), "usd_rate": float(session_state.get("base_rate", 4.25))/100, "huf_rate": float(session_state.get("quote_rate", 5.0))/100, "basis_bps": float(session_state.get("cross_currency_basis_bps", -22))}
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="6. Hedged pickup and hedge choice", page_icon="📘", layout="wide")
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[5]
    m=_get_market_state(st.session_state)
    spot,usd,huf,basis=float(m["spot_fx"]),float(m["usd_rate"]),float(m["huf_rate"]),float(m["basis_bps"])
    fwd=spot*(1+huf)/(1+usd); cf=conversion_factor_from_fx(spot,fwd)
    gross=translate_spread_bp((huf-usd)*10_000,cf)
    rows=[]
    for hc in [20.0,35.0,50.0]:
        rp=roll_cost_and_risk_proxy_bp(hc,hc+5.0,18.0,1.0)
        ch=matched_vs_rolling_hedge_economics_bp(hc+12.0,hc,rp["roll_risk_proxy_bp"],0.6)
        rows.append({"hedge_cost":hc,"pickup":hedged_pickup_bp(gross,hc,abs(basis),8.0),**rp,**ch})
    base=next(r for r in rows if r["hedge_cost"]==35.0)
    st.title("6. Hedged pickup and hedge choice")
    a,b,c=st.columns(3); a.metric("Converted gross",f"{gross:.2f} bps"); b.metric("Net pickup",f"{base['pickup']:.2f} bps"); c.metric("Preferred",str(base['preferred_hedge']).title())
    st.line_chart({"hedge_cost":[r['hedge_cost'] for r in rows],"pickup":[r['pickup'] for r in rows],"benefit_of_rolling":[r['benefit_of_rolling_bp'] for r in rows]}, x="hedge_cost")
    st.dataframe(rows,use_container_width=True)
    st.write("Hedge choice is based on risk-adjusted pickup rather than carry alone.")
    learning_hint("Rolling hedges can lose after volatility-scaled roll risk penalties.")
    render_calculation_windows([
        CalculationWindow("Conversion factor", r"CF=F/S", f"$F={fwd:.4f}, S={spot:.4f}$", ("CF translates spread across FX quote space.",), result=f"{cf:.6f}"),
        CalculationWindow("Translated gross pickup", r"\text{gross}_{tr}=\text{gross}\times CF", f"$\text{{gross}}={(huf-usd)*10_000:.2f}, CF={cf:.6f}$", ("Positive is favorable before costs.",), result=f"{gross:.2f} bps"),
        CalculationWindow("Net hedged pickup", r"\text{Net}=\text{Gross}-\text{Hedge}-\text{Basis}-\text{Extra}", f"${gross:.2f}-35.00-{abs(basis):.2f}-8.00$", ("Higher positive net is better.",), result=f"{base['pickup']:.2f} bps"),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
