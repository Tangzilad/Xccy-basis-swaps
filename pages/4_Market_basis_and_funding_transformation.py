from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.funding import (
    build_tenor_funding_table,
    four_view_funding_decomposition,
    funding_role_interpretation,
    issuance_choice,
    issuance_decision_from_spreads,
)
from src.explainers.theory_panels import render_pedagogical_scaffold
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


def _normalize_role_from_state(raw_role: object) -> str:
    role = str(raw_role or "issuer").strip().lower()
    return role if role in {"issuer", "investor", "treasury"} else "issuer"


def _recommendation_state(delta_bp: float, friction_bp: float) -> tuple[str, str]:
    if delta_bp > friction_bp:
        return "Direct route preferred", "🟥"
    if delta_bp < -friction_bp:
        return "Synthetic route preferred", "🟩"
    return "Indifferent within friction band", "🟨"


REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "theoretical_forward",
    "synthetic_funding_cost",
    "forward_difference",
)


WORKED_EXAMPLE_INPUTS = {
    "usd_spread_bp": 200.0,
    "huf_spread_bp": 100.0,
    "conversion_factor": 1.091,
    "basis_bp": 39.5,
}


def render_page() -> None:
    from streamlit_calc_helpers import (
        SignConventionContext,
        render_shared_sign_convention,
    )

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
    summary = market_context["summary_1y"]["base"]
    canonical_state = market_context["state"]

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
    one_views = four_view_funding_decomposition(
        domestic_curve_rate=float(one["HUF direct"]) - float(one["extra_spread"]),
        foreign_curve_rate=float(one["USD direct"]) - float(one["extra_spread"]),
        basis_spread=float(one["basis"]),
        extra_spread=float(one["extra_spread"]),
    )

    friction_bps_1y = float(summary["funding_friction_bps"])
    huf_choice = issuance_choice(
        issue_currency="HUF",
        direct_rate=one_views["direct_domestic"],
        swapped_rate=one_views["synthetic_domestic"],
    )
    usd_choice = issuance_choice(
        issue_currency="USD",
        direct_rate=one_views["direct_foreign"],
        swapped_rate=one_views["synthetic_foreign"],
    )

    example_decision = issuance_decision_from_spreads(**WORKED_EXAMPLE_INPUTS)
    example_usd = example_decision["USD"]
    example_huf = example_decision["HUF"]

    render_page_header(3, "4. Market Basis and Funding Transformation")

    selected_role = _normalize_role_from_state(canonical_state.get("user_role"))
    role = st.selectbox(
        "Role lens",
        options=["issuer", "investor", "treasury"],
        index=["issuer", "investor", "treasury"].index(selected_role),
        help="Role-aware interpretation text is driven by this selector and persisted in canonical shell state.",
    )
    canonical_state["user_role"] = role
    st.caption(funding_role_interpretation(role))

    # Ordered block: metrics -> chart/data -> recommendations -> calculations
    st.subheader("1Y Funding Snapshot")
    m1, m2, m3 = st.columns(3)
    m1.metric("Direct HUF all-in (1Y)", f"{one_views['direct_domestic']:.3%}")
    m2.metric("Synthetic HUF all-in (1Y)", f"{one_views['synthetic_domestic']:.3%}")
    m3.metric("HUF gap (syn - direct)", f"{one_views['domestic_delta'] * 10_000:.2f} bps")

    d1, d2, d3 = st.columns(3)
    d1.metric("Direct USD all-in (1Y)", f"{one_views['direct_foreign']:.3%}")
    d2.metric("Synthetic USD all-in (1Y)", f"{one_views['synthetic_foreign']:.3%}")
    d3.metric("USD gap (syn - direct)", f"{one_views['foreign_delta'] * 10_000:.2f} bps")

    st.subheader("Tenor-by-tenor deltas (both directions)")
    st.line_chart(
        {
            "Tenor": [r["Tenor"] for r in rows],
            "HUF delta (bps)": [float(r["HUF delta"]) * 10_000.0 for r in rows],
            "USD delta (bps)": [float(r["USD delta"]) * 10_000.0 for r in rows],
        },
        x="Tenor",
    )
    st.dataframe(rows, use_container_width=True)

    huf_state, huf_icon = _recommendation_state(one_views["domestic_delta"] * 10_000.0, friction_bps_1y)
    usd_state, usd_icon = _recommendation_state(one_views["foreign_delta"] * 10_000.0, friction_bps_1y)

    st.subheader("Issuance recommendations")
    rec_l, rec_r = st.columns(2)
    with rec_l:
        st.markdown(f"**HUF funding:** {huf_choice.preferred_route}")
        st.metric("HUF savings", f"{huf_choice.savings_bp:.1f} bps")
        st.markdown(f"{huf_icon} **{huf_state}** (Δ={one_views['domestic_delta'] * 10_000.0:.2f} bps)")
    with rec_r:
        st.markdown(f"**USD funding:** {usd_choice.preferred_route}")
        st.metric("USD savings", f"{usd_choice.savings_bp:.1f} bps")
        st.markdown(f"{usd_icon} **{usd_state}** (Δ={one_views['foreign_delta'] * 10_000.0:.2f} bps)")

    st.caption(
        f"Friction sensitivity threshold uses 1Y funding friction = {friction_bps_1y:.2f} bps from canonical market context."
    )

    st.markdown("### Issuance decision rules (spread space)")
    st.markdown(
        "- **USD issuer condition:** `USDspread > HUFspread × CF + basis` → issue HUF and swap into USD.\n"
        "- **HUF issuer reverse condition:** `HUFspread > (USDspread - basis) / CF` → issue USD and swap into HUF."
    )

    st.markdown("### Worked example (20 Feb 2017-style assumptions)")
    st.markdown(
        "Using fixed inputs in app context: USD spread **200 bp**, HUF spread **100 bp**, "
        "conversion factor **1.091**, basis **39.5 bp**."
    )
    st.markdown(
        f"- Synthetic USD spread from HUF route = `100 × 1.091 + 39.5 = {example_usd.synthetic_spread_bp:.1f} bp`.\n"
        f"- USD direct spread = `{example_usd.direct_spread_bp:.1f} bp` → recommendation: **{example_usd.preferred_route}**.\n"
        f"- USD synthetic savings = `{example_usd.savings_bp:.1f} bp` (approximately 50 bp).\n"
        f"- HUF reverse check uses `(200 - 39.5) / 1.091 = {example_huf.synthetic_spread_bp:.1f} bp` vs direct `100.0 bp`."
    )

    learning_hint(
        "Notice how the gap can flip sign across tenors. A treasurer should compare direct and synthetic routes "
        "for the full tenor ladder, not only 1Y."
    )

    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Funding decision lens (issuer/investor/treasury) for HUF and USD issuance directions.",
        positive_interpretation="Positive delta/gap means synthetic funding is more expensive than direct funding.",
        negative_interpretation="Negative delta/gap means synthetic funding is cheaper than direct funding.",
    )
    render_shared_sign_convention(sign_context)

    render_calculation_windows(
        [
            CalculationWindow(
                title="Direct HUF all-in",
                concept_meaning="Direct domestic funding rate after extra spread adjustments.",
                why_it_matters="Baseline comparator for synthetic HUF funding.",
                formula=r"r_{dir,HUF}=r_{HUF\ curve}+s_{extra}",
                methodology_rationale="Add execution spread to the HUF curve rate.",
                inputs_used="HUF curve rate and extra spread.",
                substituted_values=f"$r_{{HUF\\ curve}}={(one_views['direct_domestic'] - one_views['extra_spread']):.4%}, s_{{extra}}={one_views['extra_spread']:.4%}$",
                derivation_steps=("Read HUF curve rate.", "Add issuer extra spread.",),
                assumptions=("Inputs are tenor-aligned annualized rates.",),
                interpretation="Lower direct HUF all-in supports local issuance.",
                common_misunderstandings=("Ignoring extra spread understates executable direct cost.",),
                result=f"{one_views['direct_domestic']:.4%}",
            ),
            CalculationWindow(
                title="Synthetic HUF all-in",
                concept_meaning="HUF-equivalent funding via USD issuance and FX basis swap.",
                why_it_matters="Core synthetic comparator in the HUF funding decision.",
                formula=r"r_{syn,HUF}=r_{USD\ curve}+b+s_{extra}",
                methodology_rationale="Translate USD funding into HUF all-in terms using basis.",
                inputs_used="USD curve rate, basis, and extra spread.",
                substituted_values=f"$r_{{USD\\ curve}}={(one_views['direct_foreign'] - one_views['extra_spread']):.4%}, b={one_views['basis']:.4%}, s_{{extra}}={one_views['extra_spread']:.4%}$",
                derivation_steps=("Start from USD curve.", "Add basis transfer.", "Add extra spread.",),
                assumptions=("Basis is executed at quoted tenor level.",),
                interpretation="Compare with direct HUF to determine cheaper issuance route.",
                common_misunderstandings=("Dropping basis term invalidates synthetic all-in comparison.",),
                result=f"{one_views['synthetic_domestic']:.4%}",
            ),
            CalculationWindow(
                title="Cross-market deltas and recommendation",
                concept_meaning="Decision metric for direct vs synthetic route in both currencies.",
                why_it_matters="Negative delta indicates synthetic route savings.",
                formula=r"\Delta_{HUF}=r_{syn,HUF}-r_{dir,HUF},\;\Delta_{USD}=r_{syn,USD}-r_{dir,USD}",
                methodology_rationale="Compute signed gaps and map sign to route recommendation.",
                inputs_used="1Y direct and synthetic all-in rates from funding decomposition.",
                substituted_values=(
                    f"$\\Delta_{{HUF}}={one_views['synthetic_domestic']:.6f}-{one_views['direct_domestic']:.6f}, "
                    f"\\Delta_{{USD}}={one_views['synthetic_foreign']:.6f}-{one_views['direct_foreign']:.6f}$"
                ),
                derivation_steps=(
                    "Compute HUF and USD deltas from one source decomposition.",
                    "Interpret negative delta as synthetic savings.",
                    "Apply friction threshold for recommendation state.",
                ),
                assumptions=("Friction threshold is treated as symmetric around zero.",),
                interpretation="Signed deltas drive recommendation and savings figures.",
                common_misunderstandings=("Using absolute gaps loses the route direction signal.",),
                result=(
                    f"HUF: {huf_choice.preferred_route}; savings {huf_choice.savings_bp:.2f} bps | "
                    f"USD: {usd_choice.preferred_route}; savings {usd_choice.savings_bp:.2f} bps"
                ),
            ),
            CalculationWindow(
                title="Worked example spread rule",
                concept_meaning="Explicit issuance inequality check in spread space.",
                why_it_matters="Translates the rule into a concrete, auditable decision.",
                formula=r"USD_{dir} \overset{?}{>} HUF_{dir}\times CF + basis",
                methodology_rationale="Compare direct USD spread to synthetic USD spread created from HUF issuance.",
                inputs_used="USD spread 200 bp, HUF spread 100 bp, CF 1.091, basis 39.5 bp.",
                substituted_values=(
                    "$200 \\overset{?}{>} 100\\times1.091 + 39.5 = 148.6$; "
                    "$HUF_{syn}=(200-39.5)/1.091=147.1$"
                ),
                derivation_steps=(
                    "Compute synthetic USD spread from HUF inputs.",
                    "Compare synthetic vs direct USD spreads.",
                    "Report savings and reverse HUF check.",
                ),
                assumptions=("All quantities are in basis points and aligned to same tenor.",),
                interpretation="USD issuer prefers swapped HUF route with ~51.4 bp savings in this setup.",
                common_misunderstandings=("Confusing HUF with EUR proxy labels; app context uses HUF consistently.",),
                result=f"USD synthetic savings = {example_usd.savings_bp:.1f} bps (~50 bp)",
            ),
        ]
    )

    render_page_footer(3)


if __name__ == "__main__":
    render_page()
else:
    render_page()
