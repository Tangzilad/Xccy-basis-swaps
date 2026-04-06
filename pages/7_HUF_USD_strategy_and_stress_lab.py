from __future__ import annotations

from src.analytics.conversion_factor import conversion_factor_from_fx
from src.analytics.frictions import friction_adjusted_arbitrage_band_bp
from src.analytics.funding import all_in_funding_decomposition
from src.analytics.hedging import hedged_pickup_bp
from src.analytics.parity import fair_value_comparison
from src.analytics.xccy_swap import synthetic_funding_cost_outputs
from src.scenarios.scenario_library import SCENARIO_LIBRARY, apply_scenario


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _baseline_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {"spot_fx": float(session_state.get("spot_fx", 1.08)), "usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))), "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))), "basis_bps": float(session_state.get("cross_currency_basis_bps", -22)), "credit_spread_bp": 20.0, "funding_spread_bp": 15.0, "capital_xva_proxy_bp": 12.0, "liquidity_repo_bp": 10.0}
    session_state["market_state"] = ms
    return ms


def _to_scenario_state(base: dict) -> dict:
    return {"huf_rates": {"front": base["huf_rate"], "belly": base["huf_rate"], "back": base["huf_rate"]}, "usd_rates": {"front": base["usd_rate"], "belly": base["usd_rate"], "back": base["usd_rate"]}, "spot": base["spot_fx"], "forward_points": 0.0, "basis_curve": {"front": base["basis_bps"], "belly": base["basis_bps"], "back": base["basis_bps"]}, "credit_spreads": {"sovereign": base["credit_spread_bp"], "banks": base["credit_spread_bp"]}, "funding_spreads": {"secured": base["funding_spread_bp"], "unsecured": base["funding_spread_bp"]}, "capital_xva_proxy": base["capital_xva_proxy_bp"], "liquidity_repo_availability": base["liquidity_repo_bp"]}


def _compute_metrics(state: dict) -> dict:
    usd,huf,spot,bps=float(state["usd_rates"]["belly"]),float(state["huf_rates"]["belly"]),float(state["spot"]),float(state["basis_curve"]["belly"])
    basis=bps/10_000.0; fwd=spot*(1+(huf+basis))/(1+usd)
    parity=fair_value_comparison(spot,fwd,usd,huf,1.0)
    _=all_in_funding_decomposition(usd,huf,basis,float(state["funding_spreads"]["secured"])/10_000.0)
    fr=friction_adjusted_arbitrage_band_bp(abs(bps),float(state["capital_xva_proxy"]),float(state["funding_spreads"]["unsecured"]),float(state["credit_spreads"]["sovereign"]),float(state["credit_spreads"]["banks"])*0.4,3.0,max(0.0,25.0-float(state["liquidity_repo_availability"])))
    cf=conversion_factor_from_fx(spot,fwd)
    pk=hedged_pickup_bp((huf-usd)*10_000*cf,40.0,abs(bps),fr["total_friction_bp"]*0.1)
    syn=synthetic_funding_cost_outputs(spot,fwd,huf,basis,1.0)
    return {"spot":spot,"forward":fwd,"basis_bps":bps,"parity":parity,"frictions":fr,"conversion_factor":cf,"pickup_bp":pk,"synthetic":syn}


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="7. HUF/USD strategy and stress lab", page_icon="📘", layout="wide")
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[6]
    base=_baseline_market_state(st.session_state)
    name=st.selectbox("Scenario", list(SCENARIO_LIBRARY.keys()), index=0)
    sc=SCENARIO_LIBRARY[name]
    bm,sm=_compute_metrics(_to_scenario_state(base)),_compute_metrics(apply_scenario(sc,_to_scenario_state(base)))
    rows=[{"state":"base","basis_bps":bm["basis_bps"],"pickup_bp":bm["pickup_bp"],"raw_wedge_bp":bm["parity"]["raw_basis_wedge_bp"]},{"state":"stressed","basis_bps":sm["basis_bps"],"pickup_bp":sm["pickup_bp"],"raw_wedge_bp":sm["parity"]["raw_basis_wedge_bp"]}]
    st.title("7. HUF/USD strategy and stress lab"); st.caption(sc.description)
    a,b,c=st.columns(3); a.metric("Δ basis",f"{sm['basis_bps']-bm['basis_bps']:.2f} bps"); b.metric("Δ pickup",f"{sm['pickup_bp']-bm['pickup_bp']:.2f} bps"); c.metric("Stress actionable", "Yes" if sm["frictions"]["is_actionable"] else "No")
    st.bar_chart({"state":[r['state'] for r in rows],"basis_bps":[r['basis_bps'] for r in rows],"pickup_bp":[r['pickup_bp'] for r in rows],"raw_wedge_bp":[r['raw_wedge_bp'] for r in rows]}, x="state")
    st.dataframe(rows,use_container_width=True)
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
