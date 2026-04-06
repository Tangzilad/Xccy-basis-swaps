from __future__ import annotations

from src.analytics.funding import all_in_funding_decomposition
from src.state.session_access import get_canonical_market_context
from src.analytics.funding import (
    build_tenor_funding_table,
    funding_role_interpretation,
    issuance_choice,
)


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import (
        CalculationWindow,
        SignConventionContext,
        render_calculation_windows,
        render_shared_sign_convention,
    )
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[3]

    market_context = get_canonical_market_context(st.session_state)
    base_snapshot = market_context["base_snapshot"]
    canonical_state = market_context["state"]
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
    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
    usd = float(summary["usd_rate"])
    huf = float(summary["huf_rate"])
    basis = float(summary["basis_bps"]) / 10_000.0
    extra = 12.0 / 10_000.0

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
    friction_bps_1y = float(market_context["summary_1y"]["base"]["funding_friction_bps"])

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
    selected_role = _normalize_role_from_state(canonical_state.get("user_role"))
    role = st.selectbox(
        "Role lens",
        options=["issuer", "investor", "treasury"],
        index=["issuer", "investor", "treasury"].index(selected_role),
        help="Role-aware interpretation text is driven by this selector and persisted in canonical shell state.",
    )
    canonical_state["user_role"] = role
    st.session_state["market_state"]["user_role"] = role
    st.caption(funding_role_interpretation(role))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("HUF direction (fund into HUF)")
        a, b, c = st.columns(3)
        a.metric("Direct all-in", f"{one['HUF direct']:.3%}")
        b.metric("Synthetic all-in", f"{one['HUF synthetic']:.3%}")
        c.metric("Delta (syn - direct)", f"{one['HUF delta'] * 10000:.2f} bps")
    with c2:
        st.subheader("USD direction (fund into USD)")
        a, b, c = st.columns(3)
        a.metric("Direct all-in", f"{one['USD direct']:.3%}")
        b.metric("Synthetic all-in", f"{one['USD synthetic']:.3%}")
        c.metric("Delta (syn - direct)", f"{one['USD delta'] * 10000:.2f} bps")

    st.subheader("Tenor-by-tenor deltas (both directions)")
    st.line_chart(
        {
            "Tenor": [r["Tenor"] for r in rows],
            "HUF delta (bps)": [r["HUF delta"] * 10_000.0 for r in rows],
            "USD delta (bps)": [r["USD delta"] * 10_000.0 for r in rows],
        },
        x="Tenor",
    )
    st.dataframe(rows, use_container_width=True)

    huf_state, huf_icon = _recommendation_state(one["HUF delta"] * 10_000.0, friction_bps_1y)
    usd_state, usd_icon = _recommendation_state(one["USD delta"] * 10_000.0, friction_bps_1y)
    st.subheader("Recommendation panel (1Y)")
    r1, r2 = st.columns(2)
    r1.markdown(
        "\n".join(
            [
                f"**HUF recommendation:** {huf_icon} **{huf_state}**",
                f"- Delta: `{one['HUF delta'] * 10000:.2f} bps`",
                f"- Choice helper: `{huf_choice.preferred_route}`",
            ]
        )
    )
    r2.markdown(
        "\n".join(
            [
                f"**USD recommendation:** {usd_icon} **{usd_state}**",
                f"- Delta: `{one['USD delta'] * 10000:.2f} bps`",
                f"- Choice helper: `{usd_choice.preferred_route}`",
            ]
        )
    )
    st.caption(
        f"Friction sensitivity threshold uses 1Y funding friction = {friction_bps_1y:.2f} bps from canonical market context."
    )
    st.write("Funding transformation compares domestic route versus foreign-plus-basis route.")
    learning_hint("Positive gap means synthetic route is less economical.")
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Funding decision lens (issuer/investor/treasury) for HUF and USD issuance directions.",
        positive_interpretation="Positive delta/gap means synthetic funding is more expensive than direct funding.",
        negative_interpretation="Negative delta/gap means synthetic funding is cheaper than direct funding.",
    )
    render_shared_sign_convention(sign_context)
    render_calculation_windows([
        CalculationWindow("Domestic all-in", r"r_{dom}=r_{domcurve}+s_{extra}", f"$r_{{domcurve}}={(one['HUF direct'] - one['extra_spread']):.4%}, s_{{extra}}={one['extra_spread']:.4%}$", ("Costs add positively.",), result=f"{one['HUF direct']:.4%}"),
        CalculationWindow("Synthetic all-in", r"r_{syn}=r_{forcurve}+b+s_{extra}", f"$r_{{forcurve}}={(one['USD direct'] - one['extra_spread']):.4%}, b={one['basis']:.4%}$", ("Positive basis raises synthetic cost.",), result=f"{one['HUF synthetic']:.4%}"),
        CalculationWindow("Cross-market gap", r"\Delta r=r_{syn}-r_{dom}", f"${one['HUF synthetic']:.6f}-{one['HUF direct']:.6f}$", ("Positive gap: synthetic is worse.",), result=f"{one['HUF delta'] * 10000:.2f} bps"),
    ], sign_convention=sign_context)


if __name__ == "__main__":
    render_page()
else:
    render_page()
