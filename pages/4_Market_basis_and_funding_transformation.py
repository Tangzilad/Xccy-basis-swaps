from __future__ import annotations

import streamlit as st

from shared_page_helpers import as_decimal, get_funding_params, render_page_footer, render_page_header
from src.analytics.funding import (
    all_in_funding_decomposition,
    build_tenor_funding_table,
    issuance_choice,
)
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


def render_page() -> None:
    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[3]

    # --- Market context ---
    m = get_funding_params(st.session_state)
    usd = as_decimal(float(m["usd_rate"]))
    huf = as_decimal(float(m["huf_rate"]))
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

    # --- Header with learning objectives ---
    render_page_header(3, "4. Market Basis and Funding Transformation")

    # --- Metrics ---
    a, b, c = st.columns(3)
    a.metric("Direct HUF all-in (1Y)", f"{one['HUF direct']:.3%}")
    b.metric("Synthetic HUF all-in (1Y)", f"{one['HUF synthetic']:.3%}")
    c.metric("Gap", f"{one['HUF delta'] * 10000:.2f} bps")

    # --- Charts and data ---
    st.markdown("### Funding Gap Across Tenors")
    st.line_chart(
        {"Tenor": [r["Tenor"] for r in rows], "HUF gap": [r["HUF delta"] for r in rows], "USD gap": [r["USD delta"] for r in rows]},
        x="Tenor",
    )
    st.dataframe(rows, use_container_width=True)

    # --- Issuance recommendations ---
    st.markdown("### Issuance Route Recommendations")
    rec_l, rec_r = st.columns(2)
    with rec_l:
        st.markdown(f"**HUF funding:** {huf_choice.preferred_route}")
        st.metric("HUF savings", f"{huf_choice.savings_bp:.1f} bps")
    with rec_r:
        st.markdown(f"**USD funding:** {usd_choice.preferred_route}")
        st.metric("USD savings", f"{usd_choice.savings_bp:.1f} bps")

    st.markdown(
        "Funding transformation compares the direct issuance route versus the "
        "foreign-currency-plus-basis route. The cheaper path depends on the sign "
        "and magnitude of the cross-currency basis at each tenor."
    )

    learning_hint(
        "Notice how the gap can flip sign across tenors. This happens because basis spreads, "
        "curve slopes, and extra spreads interact differently at different maturities. "
        "A treasurer must evaluate the full tenor structure, not just the 1Y point."
    )

    # --- Calculation windows ---
    render_calculation_windows(
        [
            CalculationWindow(
                "Direct HUF all-in",
                r"r_{dir,dom}=r_{domcurve}+s_{extra}",
                f"$r_{{domcurve}}={(one['HUF direct'] - one['extra_spread']):.4%}, s_{{extra}}={one['extra_spread']:.4%}$",
                ("Costs add positively.",),
                result=f"{one['HUF direct']:.4%}",
            ),
            CalculationWindow(
                "Synthetic HUF all-in",
                r"r_{syn,dom}=r_{forcurve}+b+s_{extra}",
                f"$r_{{forcurve}}={(one['USD direct'] - one['extra_spread']):.4%}, b={one['basis']:.4%}$",
                ("Positive basis raises synthetic cost.",),
                result=f"{one['HUF synthetic']:.4%}",
            ),
            CalculationWindow(
                "Cross-market gap",
                r"\Delta r=r_{syn}-r_{dom}",
                f"${one['HUF synthetic']:.6f}-{one['HUF direct']:.6f}$",
                ("Positive gap: synthetic is more expensive. Negative gap: synthetic saves money.",),
                result=f"{one['HUF delta'] * 10000:.2f} bps",
            ),
            CalculationWindow(
                "HUF issuance choice",
                r"\Delta_{dom}=r_{syn,dom}-r_{dir,dom}",
                f"${one['HUF synthetic']:.6f}-{one['HUF direct']:.6f}$",
                ("Negative delta means swapped issuance is cheaper.",),
                result=f"{huf_choice.preferred_route}; savings {huf_choice.savings_bp:.2f} bps",
            ),
            CalculationWindow(
                "USD issuance choice",
                r"\Delta_{for}=r_{syn,for}-r_{dir,for}",
                f"${one['USD synthetic']:.6f}-{one['USD direct']:.6f}$",
                ("Negative delta means swapped issuance is cheaper.",),
                result=f"{usd_choice.preferred_route}; savings {usd_choice.savings_bp:.2f} bps",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(3)


if __name__ == "__main__":
    render_page()
else:
    render_page()
