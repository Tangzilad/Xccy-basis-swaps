from __future__ import annotations

from src.analytics.funding import (
    all_in_funding_decomposition,
    build_tenor_funding_table,
    funding_role_interpretation,
    issuance_choice,
)
from src.state.session_access import get_canonical_market_context


def _get_market_state(session_state: dict) -> object:
    return session_state.get("market_state")


def _normalize_role_from_state(raw_role: object) -> str:
    role = str(raw_role or "").strip().lower()
    if role in {"issuer", "investor", "treasury"}:
        return role
    if role in {"learning", "analyst", "risk"}:
        return "treasury"
    return "issuer"


def _recommendation_state(delta_bp: float, friction_threshold_bp: float) -> tuple[str, str]:
    if abs(delta_bp) <= friction_threshold_bp:
        return "Within friction band", "🟡"
    if delta_bp < 0:
        return "Synthetic route preferred", "✅"
    return "Direct route preferred", "⚠️"


def _normalize_role_from_state(raw_role: object) -> str:
    role = str(raw_role or "issuer").strip().lower()
    return role if role in {"issuer", "investor", "treasury"} else "issuer"


def _recommendation_state(delta_bp: float, friction_bp: float) -> tuple[str, str]:
    if delta_bp > friction_bp:
        return "Direct route preferred", "🟥"
    if delta_bp < -friction_bp:
        return "Synthetic route preferred", "🟩"
    return "Indifferent within friction band", "🟨"


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[3]
    st.title("4. Market basis and funding transformation")
    render_pedagogical_scaffold(
        st,
        page_number=4,
        learning_path=LEARNING_PATH,
        quantitative_outputs=(
            "HUF direct vs synthetic all-in rates",
            "USD direct vs synthetic all-in rates",
            "Cross-market deltas by tenor",
            "1Y recommendation state versus friction threshold",
        ),
        derivation_items=(
            ("Domestic all-in", "Add extra spread to the domestic curve rate for direct issuance cost."),
            ("Synthetic all-in", "Add basis and extra spread to foreign curve rate for swapped issuance cost."),
            ("Cross-market delta", "Subtract direct from synthetic all-in and convert to bps for route comparison."),
        ),
    )

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
    summary = market_context["summary_1y"]["base"]
    usd = float(summary["usd_rate"])
    huf = float(summary["huf_rate"])
    basis = float(summary["basis_bps"]) / 10_000.0

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
    friction_bps_1y = float(summary["funding_friction_bps"])

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
    with r1:
        st.markdown(
            "\n".join(
                [
                    f"**HUF recommendation:** {huf_icon} **{huf_state}**",
                    f"- Delta: `{one['HUF delta'] * 10000:.2f} bps`",
                    f"- Choice helper: `{huf_choice.preferred_route}`",
                ]
            )
        )
    with r2:
        st.markdown(
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
    render_calculation_windows([
        CalculationWindow(
            title="Domestic all-in",
            concept_meaning="Direct domestic funding rate after extra spread adjustments.",
            why_it_matters="Baseline comparator for synthetic funding alternatives.",
            formula=r"r_{dom}=r_{domcurve}+s_{extra}",
            methodology_rationale="Add implementation spread to underlying domestic curve rate.",
            inputs_used="Domestic curve rate and extra spread in annualized percent.",
            substituted_values=f"$r_{{domcurve}}={(one['HUF direct'] - one['extra_spread']):.4%}, s_{{extra}}={one['extra_spread']:.4%}$",
            derivation_steps=("Read direct curve rate.", "Add extra spread cost.",),
            assumptions=("Spreads add linearly.",),
            interpretation="Higher value means costlier direct HUF funding.",
            common_misunderstandings=("Omitting extra spread understates true executable cost.",),
            result=f"{one['HUF direct']:.4%}",
        ),
        CalculationWindow(
            title="Synthetic all-in",
            concept_meaning="Synthetic domestic funding from foreign curve plus basis and spread.",
            why_it_matters="Shows the executable synthetic route cost.",
            formula=r"r_{syn}=r_{forcurve}+b+s_{extra}",
            methodology_rationale="Translate foreign funding route into domestic all-in cost.",
            inputs_used="Foreign curve rate, basis, and extra spread.",
            substituted_values=f"$r_{{forcurve}}={(one['USD direct'] - one['extra_spread']):.4%}, b={one['basis']:.4%}$",
            derivation_steps=("Start from foreign direct rate.", "Add basis transfer.", "Add extra spread.",),
            assumptions=("Basis enters additively in annualized terms.",),
            interpretation="Positive basis lifts synthetic cost in this convention.",
            common_misunderstandings=("Treating basis as optional when comparing executable routes.",),
            result=f"{one['HUF synthetic']:.4%}",
        ),
        CalculationWindow(
            title="Cross-market gap",
            concept_meaning="Relative economics of synthetic versus domestic funding.",
            why_it_matters="Primary decision metric for route preference.",
            formula=r"\Delta r=r_{syn}-r_{dom}",
            methodology_rationale="Subtract direct domestic cost from synthetic all-in cost.",
            inputs_used="Synthetic and domestic all-in annualized rates.",
            substituted_values=f"${one['HUF synthetic']:.6f}-{one['HUF direct']:.6f}$",
            derivation_steps=("Compute synthetic rate.", "Compute domestic rate.", "Take difference and convert to bps.",),
            assumptions=("Both rates are tenor-aligned and annualized comparably.",),
            interpretation="Positive gap means synthetic is less economical.",
            common_misunderstandings=("Reading absolute levels without comparing the spread.",),
            result=f"{one['HUF delta'] * 10000:.2f} bps",
        ),
    ])
    render_calculation_windows(
        [
            CalculationWindow(
                "Domestic all-in",
                r"r_{dom}=r_{domcurve}+s_{extra}",
                f"$r_{{domcurve}}={(one['HUF direct'] - one['extra_spread']):.4%}, s_{{extra}}={one['extra_spread']:.4%}$",
                ("Costs add positively.",),
                result=f"{one['HUF direct']:.4%}",
            ),
            CalculationWindow(
                "Synthetic all-in",
                r"r_{syn}=r_{forcurve}+b+s_{extra}",
                f"$r_{{forcurve}}={(one['USD direct'] - one['extra_spread']):.4%}, b={one['basis']:.4%}$",
                ("Positive basis raises synthetic cost.",),
                result=f"{one['HUF synthetic']:.4%}",
            ),
            CalculationWindow(
                "Cross-market gap",
                r"\Delta r=r_{syn}-r_{dom}",
                f"${one['HUF synthetic']:.6f}-{one['HUF direct']:.6f}$",
                ("Positive gap: synthetic is worse.",),
                result=f"{one['HUF delta'] * 10000:.2f} bps",
            ),
        ]
    )


if __name__ == "__main__":
    render_page()
