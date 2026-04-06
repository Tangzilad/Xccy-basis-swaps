from __future__ import annotations

from src.analytics.funding import all_in_funding_decomposition
from src.state.session_access import get_canonical_market_context


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[3]

    base_snapshot = get_canonical_market_context(st.session_state)["base_snapshot"]
    usd_df = base_snapshot["usd_curve_df"].set_index("tenor")
    huf_df = base_snapshot["huf_curve_df"].set_index("tenor")
    basis_df = base_snapshot["basis_curve_df"].set_index("tenor")

    rows = []
    extra = 12.0 / 10_000.0
    for tenor in ["3M", "6M", "1Y", "2Y", "5Y"]:
        usd = float(usd_df.loc[tenor, "usd_zero_rate"])
        huf = float(huf_df.loc[tenor, "huf_zero_rate"])
        basis = float(basis_df.loc[tenor, "basis_bps"]) / 10_000.0
        rows.append({"Tenor": tenor, **all_in_funding_decomposition(usd, huf, basis, extra)})

    one = next(r for r in rows if r["Tenor"] == "1Y")
    st.title("4. Market basis and funding transformation")
    a, b, c = st.columns(3)
    a.metric("Direct all-in", f"{one['domestic_all_in']:.3%}")
    b.metric("Synthetic all-in", f"{one['synthetic_all_in']:.3%}")
    c.metric("Gap", f"{one['cross_market_gap'] * 10000:.2f} bps")
    st.line_chart({"Tenor": [r['Tenor'] for r in rows], "gap": [r['cross_market_gap'] for r in rows]}, x="Tenor")
    st.dataframe(rows, use_container_width=True)
    st.write("Funding transformation compares domestic route versus foreign-plus-basis route.")
    learning_hint("Positive gap means synthetic route is less economical.")
    render_calculation_windows([
        CalculationWindow("Domestic all-in", r"r_{dom}=r_{domcurve}+s_{extra}", f"$r_{{domcurve}}={one['domestic_curve']:.4%}, s_{{extra}}={one['extra_spread']:.4%}$", ("Costs add positively.",), result=f"{one['domestic_all_in']:.4%}"),
        CalculationWindow("Synthetic all-in", r"r_{syn}=r_{forcurve}+b+s_{extra}", f"$r_{{forcurve}}={one['foreign_curve']:.4%}, b={one['basis']:.4%}$", ("Positive basis raises synthetic cost.",), result=f"{one['synthetic_all_in']:.4%}"),
        CalculationWindow("Cross-market gap", r"\Delta r=r_{syn}-r_{dom}", f"${one['synthetic_all_in']:.6f}-{one['domestic_all_in']:.6f}$", ("Positive gap: synthetic is worse.",), result=f"{one['cross_market_gap'] * 10000:.2f} bps"),
    ])
