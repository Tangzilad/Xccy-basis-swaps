from __future__ import annotations

from src.analytics.funding import all_in_funding_decomposition


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {"usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))), "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))), "basis_bps": float(session_state.get("cross_currency_basis_bps", -22)), "extra_spread_bps": 12.0}
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[3]
    m = _get_market_state(st.session_state)
    usd, huf, basis, extra = _as_decimal(float(m["usd_rate"])), _as_decimal(float(m["huf_rate"])), float(m["basis_bps"]) / 10_000.0, float(m["extra_spread_bps"]) / 10_000.0
    rows=[]
    for t,s in zip(["3M","6M","1Y","2Y","5Y"],[0.9,1.0,1.05,1.1,1.2], strict=True):
        rows.append({"Tenor":t, **all_in_funding_decomposition(usd+0.0005*s,huf+0.0008*s,basis*s,extra)})
    one=next(r for r in rows if r["Tenor"]=="1Y")
    st.title("4. Market basis and funding transformation")
    a,b,c=st.columns(3); a.metric("Direct all-in",f"{one['domestic_all_in']:.3%}"); b.metric("Synthetic all-in",f"{one['synthetic_all_in']:.3%}"); c.metric("Gap",f"{one['cross_market_gap']*10000:.2f} bps")
    st.line_chart({"Tenor":[r['Tenor'] for r in rows],"gap":[r['cross_market_gap'] for r in rows]}, x="Tenor")
    st.dataframe(rows,use_container_width=True)
    st.write("Funding transformation compares domestic route versus foreign-plus-basis route.")
    learning_hint("Positive gap means synthetic route is less economical.")
    render_calculation_windows([
        CalculationWindow("Domestic all-in", r"r_{dom}=r_{domcurve}+s_{extra}", f"$r_{{domcurve}}={one['domestic_curve']:.4%}, s_{{extra}}={one['extra_spread']:.4%}$", ("Costs add positively.",), result=f"{one['domestic_all_in']:.4%}"),
        CalculationWindow("Synthetic all-in", r"r_{syn}=r_{forcurve}+b+s_{extra}", f"$r_{{forcurve}}={one['foreign_curve']:.4%}, b={one['basis']:.4%}$", ("Positive basis raises synthetic cost.",), result=f"{one['synthetic_all_in']:.4%}"),
        CalculationWindow("Cross-market gap", r"\Delta r=r_{syn}-r_{dom}", f"${one['synthetic_all_in']:.6f}-{one['domestic_all_in']:.6f}$", ("Positive gap: synthetic is worse.",), result=f"{one['cross_market_gap']*10000:.2f} bps"),
    ])
