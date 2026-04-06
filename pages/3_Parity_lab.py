from __future__ import annotations

from src.analytics.parity import fair_value_comparison, implied_huf_rate_from_spot_forward, implied_usd_rate_from_spot_forward


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {"spot_fx": float(session_state.get("spot_fx", 1.08)), "usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))), "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))), "basis_bps": float(session_state.get("cross_currency_basis_bps", -22))}
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="3. Parity lab", page_icon="📘", layout="wide")
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[2]
    m = _get_market_state(st.session_state)
    spot, usd, huf, basis = float(m["spot_fx"]), _as_decimal(float(m["usd_rate"])), _as_decimal(float(m["huf_rate"])), float(m["basis_bps"]) / 10_000.0
    rows = []
    for t in [0.25, 0.5, 1.0, 2.0]:
        obs = spot * (1 + (huf + basis) * t) / (1 + usd * t)
        rows.append({"tenor": t, **fair_value_comparison(spot, obs, usd, huf, t)})
    one = next(r for r in rows if r["tenor"] == 1.0)
    ih, iu = implied_huf_rate_from_spot_forward(spot, one["observed_forward"], usd, 1.0), implied_usd_rate_from_spot_forward(spot, one["observed_forward"], huf, 1.0)
    st.title("3. Parity lab")
    a,b,c=st.columns(3); a.metric("Observed 1Y", f"{one['observed_forward']:.4f}"); b.metric("Fair 1Y", f"{one['fair_forward_no_basis']:.4f}"); c.metric("Raw wedge", f"{one['raw_basis_wedge_bp']:.2f} bps")
    st.line_chart({"tenor":[r['tenor'] for r in rows], "wedge":[r['raw_basis_wedge_bp'] for r in rows]}, x="tenor")
    st.dataframe(rows, use_container_width=True)
    st.write("Observed forwards are benchmarked versus no-basis CIP fair values.")
    learning_hint("Persistent wedge signals parity stress.")
    render_calculation_windows([
        CalculationWindow("CIP theoretical forward", r"F=S\frac{1+r_{HUF}T}{1+r_{USD}T}", f"$S={spot:.4f}, r_{{HUF}}={huf:.4%}, r_{{USD}}={usd:.4%}$", ("Higher HUF rate lifts forward.",), result=f"{one['fair_forward_no_basis']:.4f}"),
        CalculationWindow("Implied HUF rate", r"r_{HUF}^{impl}=\frac{(F/S)(1+r_{USD}T)-1}{T}", f"$F={one['observed_forward']:.4f}$", ("Positive gap = richer implied HUF.",), result=f"{ih:.4%}"),
        CalculationWindow("Implied USD rate", r"r_{USD}^{impl}=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}", f"$F={one['observed_forward']:.4f}$", ("Higher implied USD worsens synthetic borrowing.",), result=f"{iu:.4%}"),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
