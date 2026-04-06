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
            formula=r"F_{CIP}=S\frac{1+r_f}{1+r_d}\quad\text{(app quote: HUF/USD)}",
            methodology="Apply covered interest parity with HUF-per-USD quote convention.",
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=(
                f"$S={spot:.4f}, F_{{obs}}={observed_forward:.4f}, r_d={usd_rate:.4%}, "
                f"r_f={huf_rate:.4%}, T={tenor_years:.2f}$"
            ),
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
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=(
                f"$S={spot:.4f}, F_{{obs}}={observed_forward:.4f}, r_d={usd_rate:.4%}, "
                f"r_f={huf_rate:.4%}, T={tenor_years:.2f}$"
            ),
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
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=(
                f"$S={spot:.4f}, F_{{obs}}={observed_forward:.4f}, r_d={usd_rate:.4%}, "
                f"r_f={huf_rate:.4%}, T={tenor_years:.2f}$"
            ),
            derivation_steps=("Build HUF accrual factor.", "Divide by forward ratio.", "Convert to annualized implied USD rate.",),
            assumptions=("Single-period parity approximation.",),
            interpretation="Higher implied USD means worse synthetic USD funding.",
            common_misunderstandings=("Confusing implied USD with actual policy rate expectations.",),
            result=f"{breakdown['implied_usd_rate']:.4%}",
        ),
        "raw_basis_wedge": CalculationWindow(
            title="Raw basis wedge",
            meaning="Gap between observed and no-basis theoretical forward under app quote convention.",
            significance="Core parity stress signal under a consistent sign convention.",
            formula=r"\text{Wedge}=F_{obs}-F_{CIP}",
            methodology="Take observed forward minus no-basis theoretical forward.",
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=f"$F_{{obs}}-F_{{CIP}}={observed_forward:.4f}-{breakdown['cip_implied_forward']:.4f}$",
            derivation_steps=("Compute no-basis CIP forward.", "Subtract CIP forward from observed forward.",),
            result=f"{breakdown['forward_difference']:.4f}",
            assumptions=("HUF/USD quote convention is preserved throughout.",),
            interpretation="Positive = observed forward above no-basis CIP under HUF/USD convention.",
            common_misunderstandings=(
                "Negative wedge does not necessarily imply free arbitrage after costs.",
                "Sign flips if quote convention changes.",
            ),
        ),
        "forward_difference": CalculationWindow(
            title="Forward difference",
            meaning="Absolute forward mispricing under no-basis CIP.",
            significance="Direct quote-space deviation used in diagnostics.",
            formula=r"\Delta F = F_{obs} - F_{CIP}",
            methodology="Subtract theoretical forward from observed forward.",
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=f"$\Delta F={observed_forward:.4f}-{breakdown['cip_implied_forward']:.4f}$",
            derivation_steps=("Compute CIP forward from spot and rates.", "Take observed minus CIP level.",),
            assumptions=("Inputs are tenor-matched under HUF/USD convention.",),
            interpretation="Positive values indicate observed forward richness vs CIP.",
            common_misunderstandings=("Forward difference is not yet a tradable PnL number after frictions.",),
            result=f"{breakdown['forward_difference']:.4f}",
        ),
        "relative_forward_difference": CalculationWindow(
            title="Relative forward difference",
            meaning="Forward mispricing scaled by theoretical forward, shown in bp.",
            significance="Scale-invariant way to compare wedge size across levels/tenors.",
            formula=r"\Delta F_{bp}=\frac{F_{obs}-F_{CIP}}{F_{CIP}}\times10{,}000",
            methodology="Normalize forward difference by CIP forward and convert to bp.",
            inputs="Spot (HUF/USD), observed forward (HUF/USD), domestic rate (USD), foreign rate (HUF), tenor.",
            substituted_values=(
                f"$(({observed_forward:.4f}-{breakdown['cip_implied_forward']:.4f})/"
                f"{breakdown['cip_implied_forward']:.4f})\\times10,000$"
            ),
            derivation_steps=("Compute absolute forward difference.", "Divide by CIP forward.", "Scale by 10,000.",),
            assumptions=("CIP forward is non-zero for the selected inputs.",),
            interpretation="Same sign as forward difference; larger magnitude = larger relative dislocation.",
            common_misunderstandings=("Do not confuse this quote-space bp metric with rate-basis bp directly.",),
            result=f"{breakdown['forward_relative_bp']:.2f} bp",
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
    render_required_calculation_windows(
        calc_windows,
        required_keys=REQUIRED_CALCULATION_WINDOWS,
        page_name="3. Parity lab",
        default_expanded=False,
        sign_convention=sign_context,
    )

    st.markdown("### Derivations")
    with st.expander("CIP derivation from two funding paths", expanded=False):
        st.markdown(
            "Path A (domestic funding): borrow 1 USD at domestic rate and repay "
            r"$1+r_dT$. Hedge via spot/forward gives terminal foreign-currency cashflow "
            r"$S(1+r_fT)$. No-arbitrage implies $F_{CIP}/S=(1+r_fT)/(1+r_dT)$."
        )
    with st.expander("Substitution with current inputs", expanded=False):
        st.latex(
            rf"F_{{CIP}}={spot:.4f}\times\frac{{1+({huf_rate:.6f})\times {tenor_years:.2f}}}"
            rf"{{1+({usd_rate:.6f})\times {tenor_years:.2f}}}={breakdown['cip_implied_forward']:.4f}"
        )
        st.latex(
            rf"\Delta F = F_{{obs}}-F_{{CIP}}={observed_forward:.4f}-{breakdown['cip_implied_forward']:.4f}"
            rf"={breakdown['forward_difference']:.4f}"
        )
    with st.expander("Forward mispricing and implied-rate spread equivalence", expanded=False):
        st.markdown(
            r"From $r_f^{impl}=\frac{(F/S)(1+r_dT)-1}{T}$, the spread is "
            r"$r_f^{impl}-r_f=\frac{(F-F_{CIP})(1+r_dT)}{ST}$. "
            "So the sign of forward mispricing matches the sign of implied-rate spread."
        )
        st.latex(
            rf"r_f^{{impl}}-r_f={breakdown['implied_huf_rate'] - huf_rate:.6f}"
            rf"\quad\Longleftrightarrow\quad F_{{obs}}-F_{{CIP}}={breakdown['forward_difference']:.4f}"
        )

    with st.expander("Historical context: 2008–2011 basis persistence", expanded=False):
        st.markdown(
            "During the 2008 global funding shock and the 2009–2011 aftermath, covered-interest "
            "parity deviations persisted for years rather than days. Policy support narrowed extremes, "
            "but dealer balance-sheet constraints, dollar-funding scarcity, and regulatory pressure kept "
            "basis wedges from mean-reverting quickly. The key lesson for this lab: a non-zero wedge can "
            "be structurally persistent even when textbook arbitrage appears available."
        )

    # --- Pedagogical footer ---
    render_page_footer(2)


if __name__ == "__main__":
    render_page()
else:
    render_page()
