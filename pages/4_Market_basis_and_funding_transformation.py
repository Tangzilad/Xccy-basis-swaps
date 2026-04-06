from __future__ import annotations

from src.analytics.funding import all_in_funding_decomposition
from src.state.session_access import get_canonical_market_context
from src.analytics.funding import (
    build_tenor_funding_table,
    funding_calculation_windows_payload,
    funding_role_interpretation,
    issuance_choice,
)


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {
        "usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))),
        "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))),
        "basis_bps": float(session_state.get("cross_currency_basis_bps", -22)),
        "extra_spread_bps": 12.0,
    }
    session_state["market_state"] = ms
    return ms


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
    m = _get_market_state(st.session_state)
    usd = _as_decimal(float(m["usd_rate"]))
    huf = _as_decimal(float(m["huf_rate"]))
    basis = float(m["basis_bps"]) / 10_000.0
    extra = float(m["extra_spread_bps"]) / 10_000.0

    tenors = ("3M", "6M", "1Y", "2Y", "5Y")
    scales = (0.9, 1.0, 1.05, 1.1, 1.2)
    rows = build_tenor_funding_table(
        domestic_label="HUF",
        foreign_label="USD",
        domestic_curve_rate=huf,
        foreign_curve_rate=usd,
        basis_spread=basis,
        extra_spread=extra,
        tenors=tenors,
        tenor_scales=scales,
        domestic_curve_slope=0.0008,
        foreign_curve_slope=0.0005,
    )
    one = next(r for r in rows if r["Tenor"] == "1Y")

    huf_choice = issuance_choice(
        issue_currency="HUF",
        direct_rate=float(one["HUF direct"]),
        swapped_rate=float(one["HUF synthetic"]),
    )
    usd_choice = issuance_choice(
        issue_currency="USD",
        direct_rate=float(one["USD direct"]),
        swapped_rate=float(one["USD synthetic"]),
    )

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


if __name__ == "__main__":
    render_page()
else:
    render_page()
