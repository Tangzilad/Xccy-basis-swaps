from __future__ import annotations

import streamlit as st

from shared_page_helpers import (
    render_page_footer,
    render_page_header,
)
from src.analytics.parity import (
    fair_value_comparison,
    parity_decomposition,
    tenor_ladder_decomposition,
    tenor_to_year_fraction,
)
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


TENOR_LADDER = ["3M", "6M", "1Y", "2Y", "5Y", "10Y"]
WORKED_EXAMPLE = {
    "spot": 360.0,
    "observed_forward": 369.2,
    "usd_rate": 4.65,
    "huf_rate": 6.85,
    "tenor": "1Y",
}


REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "theoretical_forward",
    "implied_huf_rate",
    "implied_usd_rate",
    "forward_difference",
    "relative_forward_difference",
    "raw_basis_wedge",
)


def _from_decimal(v: float) -> float:
    return v * 100.0 if v < 1 else v


def _parity_page_state(session_state: dict) -> dict:
    market_state = session_state.setdefault("market_state", {})
    page_state = market_state.setdefault("page_state", {})
    parity_state = page_state.setdefault("parity_lab", {})
    if not isinstance(parity_state, dict):
        parity_state = {}
        page_state["parity_lab"] = parity_state
    return parity_state


def render_page() -> None:
    from streamlit_calc_helpers import (
        SignConventionContext,
        render_shared_sign_convention,
    )

    st.set_page_config(page_title="3. Parity lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[2]

    # --- Market context ---
    context = get_canonical_market_context(st.session_state)
    summary = context["summary_1y"]["base"]
    spot_ctx = float(summary["spot_fx"])
    usd_ctx = float(summary["usd_rate"])
    huf_ctx = float(summary["huf_rate"])
    basis_ctx = float(summary["basis_bps"]) / 10_000.0

    # --- Header with learning objectives ---
    render_page_header(2, "3. Parity Lab")
    st.caption("Inputs and outputs follow HUF per USD FX quote convention.")

    # --- Quick tenor overview (from canonical state) ---
    st.markdown("### Tenor Overview")
    rows = []
    for t in [0.25, 0.5, 1.0, 2.0]:
        obs = spot_ctx * (1 + (huf_ctx + basis_ctx) * t) / (1 + usd_ctx * t)
        rows.append({"tenor": t, **fair_value_comparison(spot_ctx, obs, usd_ctx, huf_ctx, t)})
    one = next(r for r in rows if r["tenor"] == 1.0)

    a, b, c = st.columns(3)
    a.metric("Observed 1Y", f"{one['observed_forward']:.4f}")
    b.metric("Fair 1Y", f"{one['fair_forward_no_basis']:.4f}")
    c.metric("Raw wedge", f"{one['raw_basis_wedge_bp']:.2f} bps")

    st.line_chart(
        {"tenor": [r["tenor"] for r in rows], "wedge": [r["raw_basis_wedge_bp"] for r in rows]},
        x="tenor",
    )

    learning_hint(
        "The chart above shows how the raw basis wedge evolves across tenors. "
        "In CIP-perfect markets this line would be flat at zero. Deviations reveal "
        "balance-sheet constraints or hedging demand imbalances."
    )

    # --- Interactive parity decomposition ---
    st.markdown("### Interactive Decomposition")

    st.title("3. Parity lab")
    parity_state = _parity_page_state(st.session_state)
    base_summary = context["summary_1y"]["base"]
    default_spot = float(base_summary["spot_fx"])
    default_usd = _from_decimal(float(base_summary["usd_rate"]))
    default_huf = _from_decimal(float(base_summary["huf_rate"]))

    button = getattr(st, "button", None)
    st.subheader("Canonical inputs")
    if callable(button) and button("Worked example (HUF/USD)"):
        parity_state["spot"] = WORKED_EXAMPLE["spot"]
        parity_state["forward"] = WORKED_EXAMPLE["observed_forward"]
        parity_state["usd_rate_pct"] = WORKED_EXAMPLE["usd_rate"]
        parity_state["huf_rate_pct"] = WORKED_EXAMPLE["huf_rate"]
        parity_state["tenor"] = WORKED_EXAMPLE["tenor"]

    left, right = st.columns(2)
    with left:
        spot = float(
            st.number_input(
                "Spot (HUF per USD)",
                min_value=0.0001,
                value=float(parity_state.get("spot", default_spot)),
                step=0.01,
            )
        )
        parity_state["spot"] = spot
        observed_forward = float(
            st.number_input(
                "Observed forward (HUF per USD)",
                min_value=0.0001,
                value=float(parity_state.get("forward", default_spot)),
                step=0.01,
            )
        )
        parity_state["forward"] = observed_forward
        tenor_label = st.selectbox(
            "Tenor",
            TENOR_LADDER,
            index=TENOR_LADDER.index(parity_state.get("tenor", "1Y")),
        )
        parity_state["tenor"] = tenor_label
    with right:
        usd_rate_pct = float(
            st.number_input(
                "USD rate (%)",
                value=float(parity_state.get("usd_rate_pct", default_usd)),
                step=0.05,
            )
        )
        parity_state["usd_rate_pct"] = usd_rate_pct
        huf_rate_pct = float(
            st.number_input(
                "HUF rate (%)",
                value=float(parity_state.get("huf_rate_pct", default_huf)),
                step=0.05,
            )
        )
        parity_state["huf_rate_pct"] = huf_rate_pct

    usd_rate = usd_rate_pct / 100.0
    huf_rate = huf_rate_pct / 100.0
    tenor_years = tenor_to_year_fraction(tenor_label)

    breakdown = parity_decomposition(
        spot_huf_per_usd=spot,
        observed_forward_huf_per_usd=observed_forward,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=tenor_years,
    )

    # --- Metrics ---
    st.markdown("### Results")
    ladder = tenor_ladder_decomposition(
        spot_huf_per_usd=spot,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        tenor_labels=TENOR_LADDER,
        anchor_observed_forward=observed_forward,
        anchor_tenor_label=tenor_label,
    )
    one = next(row for row in ladder if row["tenor"] == "1Y")

    summary_a, summary_b, summary_c = st.columns(3)
    summary_a.metric("Observed 1Y", f"{one['observed_forward']:.4f}")
    summary_b.metric("Fair 1Y", f"{one['cip_implied_forward']:.4f}")
    summary_c.metric("Raw wedge", f"{one['raw_basis_wedge_bp']:.2f} bps")

    st.subheader("Decomposition outputs")
    c1, c2, c3 = st.columns(3)
    c1.metric("CIP-implied forward", f"{breakdown['cip_implied_forward']:.4f}")
    c2.metric("Implied HUF rate", f"{breakdown['implied_huf_rate']:.4%}")
    c3.metric("Implied USD rate", f"{breakdown['implied_usd_rate']:.4%}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Forward difference", f"{breakdown['forward_difference']:.4f}")
    c5.metric("Relative forward diff", f"{breakdown['forward_relative_bp']:.2f} bp")
    c6.metric("Raw basis wedge", f"{breakdown['raw_basis_wedge_bp']:.2f} bp")

    st.markdown(
        "**Sign convention (HUF per USD):** "
        "A **positive** raw basis wedge means the observed forward is high vs no-basis CIP, "
        "so implied HUF funding is richer (worse for synthetic USD borrowing via HUF). "
        "A **negative** wedge means observed forward is low vs CIP and synthetic USD funding is cheaper."
    )

    # --- Tenor ladder ---
    st.markdown("### Tenor Ladder")
    ladder = tenor_ladder_decomposition(
        spot_huf_per_usd=spot,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        tenor_labels=TENOR_LADDER,
        anchor_observed_forward=observed_forward,
        anchor_tenor_label=tenor_label,
    )
    st.line_chart(
        {
            "tenor": [row["tenor"] for row in ladder],
            "observed_forward": [row["observed_forward"] for row in ladder],
            "cip_implied_forward": [row["cip_implied_forward"] for row in ladder],
        },
        x="tenor",
    )
    st.line_chart(
        {
            "tenor": [row["tenor"] for row in ladder],
            "raw_basis_wedge_bp": [row["raw_basis_wedge_bp"] for row in ladder],
        },
        x="tenor",
    )
    st.dataframe(
        [
            {
                "tenor": row["tenor"],
                "observed_forward": row["observed_forward"],
                "cip_implied_forward": row["cip_implied_forward"],
                "forward_difference": row["forward_difference"],
                "forward_relative_bp": row["forward_relative_bp"],
                "raw_basis_wedge_bp": row["raw_basis_wedge_bp"],
            }
            for row in ladder
        ],
        use_container_width=True,
    )
    st.write("Observed forwards are benchmarked versus no-basis CIP fair values.")

    learning_hint(
        "Compare the two forward curves above. Where they diverge most is where basis "
        "pressure is greatest. Ask yourself: is the wedge driven by rate differentials, "
        "FX supply-demand, or balance-sheet constraints?"
    )

    # --- Calculation windows ---
    calc_windows = {
        "theoretical_forward": CalculationWindow(
            title="Theoretical forward",
            meaning="No-basis CIP-implied forward under current spot and interest curves.",
            significance="Reference level used to diagnose parity dislocations.",
            formula=r"F_{CIP}=S\frac{1+r_{HUF}T}{1+r_{USD}T}",
            methodology="Apply covered interest parity with HUF-per-USD quote convention.",
            inputs="Spot (HUF/USD), HUF and USD annualized rates, tenor in years.",
            substituted_values=f"$S={spot:.4f}, r_{{HUF}}={huf_rate:.4%}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$",
            derivation_steps=("Compute gross HUF and USD accrual factors.", "Take their ratio.", "Multiply by spot.",),
            assumptions=("Simple compounding over tenor T.",),
            interpretation="Higher HUF rates raise the no-basis HUF-per-USD forward.",
            common_misunderstandings=("Treating CIP forward as identical to observed forward in stressed markets.",),
            result=f"{breakdown['cip_implied_forward']:.4f}",
            expanded=True,
        ),
        "implied_huf_rate": CalculationWindow(
            title="Implied HUF rate",
            meaning="HUF rate implied by observed spot-forward pair given USD curve.",
            significance="Lets us compare market-implied HUF funding versus curve HUF funding.",
            formula=r"r_{HUF}^{impl}=\frac{(F/S)(1+r_{USD}T)-1}{T}",
            methodology="Rearrange CIP to solve for HUF rate from observed forward.",
            inputs="Observed forward, spot, USD rate, tenor.",
            substituted_values=f"$F={observed_forward:.4f}, S={spot:.4f}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$",
            derivation_steps=("Compute forward ratio F/S.", "Scale by USD accrual factor.", "Back out annualized implied HUF rate.",),
            assumptions=("Observed forward is executable for chosen tenor.",),
            interpretation="Above market HUF curve implies positive wedge.",
            common_misunderstandings=("Comparing implied HUF directly to USD curve instead of HUF curve.",),
            result=f"{breakdown['implied_huf_rate']:.4%}",
        ),
        "implied_usd_rate": CalculationWindow(
            title="Implied USD rate",
            meaning="USD rate implied by observed forward when HUF curve is taken as anchor.",
            significance="Represents synthetic USD funding cost inferred from FX markets.",
            formula=r"r_{USD}^{impl}=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}",
            methodology="Solve CIP inversion for USD side while holding HUF curve fixed.",
            inputs="Observed forward, spot, HUF rate, tenor.",
            substituted_values=f"$F={observed_forward:.4f}, S={spot:.4f}, r_{{HUF}}={huf_rate:.4%}, T={tenor_years:.2f}$",
            derivation_steps=("Build HUF accrual factor.", "Divide by forward ratio.", "Convert to annualized implied USD rate.",),
            assumptions=("Single-period parity approximation.",),
            interpretation="Higher implied USD means worse synthetic USD funding.",
            common_misunderstandings=("Confusing implied USD with actual policy rate expectations.",),
            result=f"{breakdown['implied_usd_rate']:.4%}",
        ),
        "raw_basis_wedge": CalculationWindow(
            title="Raw basis wedge",
            meaning="Gap between implied and curve HUF funding in basis points.",
            significance="Core parity stress signal under a consistent sign convention.",
            formula=r"\text{Wedge}_{bp}=(r_{HUF}^{impl}-r_{HUF})\times 10{,}000",
            methodology="Compare implied HUF rate from FX with direct HUF curve rate.",
            inputs="Implied HUF rate and market HUF curve rate.",
            substituted_values=f"$({breakdown['implied_huf_rate']:.6f}-{huf_rate:.6f})\\times10,000$",
            derivation_steps=("Compute implied-minus-curve spread.", "Multiply by 10,000 to express bps.",),
            result=f"{breakdown['raw_basis_wedge_bp']:.2f} bp",
            assumptions=("HUF/USD quote convention is preserved throughout.",),
            interpretation="Positive = observed forward above no-basis CIP under HUF/USD convention.",
            common_misunderstandings=(
                "Negative wedge does not necessarily imply free arbitrage after costs.",
                "Sign flips if quote convention changes.",
            ),
        ),
        "synthetic_funding_cost": CalculationWindow(
            title="Synthetic funding cost",
            meaning="Approximate synthetic USD borrowing cost inferred from parity.",
            significance="Connects parity decomposition to funding decision-making.",
            formula=r"\text{Synthetic USD cost} \approx r_{USD}^{impl}",
            methodology="Use implied USD rate as first-pass synthetic funding estimate.",
            inputs="Implied USD rate extracted from spot-forward parity.",
            substituted_values="Using implied USD rate from spot-forward parity decomposition.",
            derivation_steps=("Compute implied USD rate.", "Use as synthetic funding proxy.",),
            assumptions=("Secondary execution frictions are excluded on this page.",),
            interpretation="Higher implied value means poorer synthetic funding economics.",
            common_misunderstandings=("Assuming this already includes transaction/friction adjustments.",),
            result=f"{breakdown['implied_usd_rate']:.4%}",
        ),
        "friction_adjusted_arbitrage_band": CalculationWindow(
            title="Friction-adjusted arbitrage band",
            meaning="Placeholder for translating raw wedge into tradable edge after frictions.",
            significance="Introduces the transition from parity diagnosis to executable arbitrage economics.",
            formula=r"\text{Net edge}=\text{Raw wedge}-\text{Frictions}",
            methodology="Subtract estimated frictions from raw wedge once implementation costs are modeled.",
            inputs="Raw wedge and friction estimates (introduced on later pages).",
            substituted_values="Friction inputs are not modelled on this page; interpret raw wedge before costs.",
            derivation_steps=("Start from raw wedge.", "Deduct friction stack.", "Interpret residual tradable edge.",),
            assumptions=("Friction decomposition is delegated to later modules.",),
            interpretation="Not computed here; sign should be read under the shared page convention.",
            common_misunderstandings=("Treating raw wedge as executable arbitrage without costs.",),
            result="See page 5",
        ),
        "hedged_pickup": CalculationWindow(
            title="Hedged pickup",
            meaning="Risk-managed carry after hedge and basis implementation costs.",
            significance="Critical metric for strategy attractiveness.",
            formula=r"\text{Pickup}=\text{Carry}-\text{Hedge costs}",
            methodology="Later modules decompose carry into executable net pickup.",
            inputs="Carry, hedge cost, basis drag, and friction terms (later pages).",
            substituted_values="Carry and hedge implementation are shown in later pages.",
            derivation_steps=("Compute gross carry.", "Subtract hedge implementation costs.", "Subtract residual frictions.",),
            assumptions=("Placeholder only on this parity-focused page.",),
            interpretation="Not computed here; introduced to maintain conceptual continuity.",
            common_misunderstandings=("Confusing nominal yield differential with hedged pickup.",),
            result="N/A on this page",
        ),
        "conversion_factor": CalculationWindow(
            title="Conversion factor",
            meaning="Direct quote-space mapping ratio between forward and spot.",
            significance="Used to translate spreads consistently across quote-space representations.",
            formula=r"CF=F/S",
            methodology="Compute tenor-matched forward divided by spot.",
            inputs="Observed forward and spot in HUF per USD.",
            substituted_values=f"$CF={observed_forward:.4f}/{spot:.4f}$",
            derivation_steps=("Collect tenor-matched forward and spot.", "Compute ratio F/S.",),
            assumptions=("Forward and spot use the same quote convention.",),
            interpretation="Higher CF implies stronger forward premium in HUF-per-USD terms.",
            common_misunderstandings=("Mixing quote conventions before taking the ratio.",),
            result=f"{observed_forward / spot:.6f}",
        ),
        "stressed_vs_base_deltas": CalculationWindow(
            title="Stressed vs base deltas",
            meaning="Scenario-change metric between stress and baseline states.",
            significance="Supports attribution when moving from diagnosis to stress testing.",
            formula=r"\Delta x = x_{stress}-x_{base}",
            methodology="Simple difference operator over matched metrics.",
            inputs="Stress and base metric values for the same quantity.",
            substituted_values="This page displays current-state decomposition only.",
            derivation_steps=("Take stressed metric.", "Subtract base metric.",),
            assumptions=("Scenario engine is used on dedicated stress page.",),
            interpretation="Not calculated here; placeholder for downstream scenario module.",
            common_misunderstandings=("Interpreting placeholder as computed output.",),
            result="N/A on this page",
        ),
    }
    st.subheader("Calculation windows")
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Parity decomposition from synthetic USD funding view via HUF market and observed forwards.",
        positive_interpretation="Positive wedge/relative difference means observed forward is above no-basis CIP.",
        negative_interpretation="Negative wedge/relative difference means observed forward is below no-basis CIP.",
    )
    render_shared_sign_convention(sign_context)
    render_required_calculation_windows(calc_windows, default_expanded=False, sign_convention=sign_context)

    # --- Pedagogical footer ---
    render_page_footer(2)


if __name__ == "__main__":
    render_page()
else:
    render_page()
