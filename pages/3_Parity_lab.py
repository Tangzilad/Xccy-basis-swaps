from __future__ import annotations

import streamlit as st

from shared_page_helpers import (
    as_decimal,
    from_decimal,
    get_market_params,
    render_page_footer,
    render_page_header,
)
from src.analytics.parity import (
    fair_value_comparison,
    implied_huf_rate_from_spot_forward,
    implied_usd_rate_from_spot_forward,
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


def render_page() -> None:
    st.set_page_config(page_title="3. Parity lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[2]

    # --- Market context ---
    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
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

    m = get_market_params(st.session_state)
    default_spot = float(m["spot_fx"])
    default_usd = from_decimal(float(m["usd_rate"]))
    default_huf = from_decimal(float(m["huf_rate"]))

    if st.button("Load worked example (HUF/USD)"):
        st.session_state["parity_spot"] = WORKED_EXAMPLE["spot"]
        st.session_state["parity_forward"] = WORKED_EXAMPLE["observed_forward"]
        st.session_state["parity_usd_rate_pct"] = WORKED_EXAMPLE["usd_rate"]
        st.session_state["parity_huf_rate_pct"] = WORKED_EXAMPLE["huf_rate"]
        st.session_state["parity_tenor"] = WORKED_EXAMPLE["tenor"]

    left, right = st.columns(2)
    with left:
        spot = float(
            st.number_input(
                "Spot (HUF per USD)",
                min_value=0.0001,
                value=float(st.session_state.get("parity_spot", default_spot)),
                step=0.01,
                key="parity_spot",
            )
        )
        observed_forward = float(
            st.number_input(
                "Observed forward (HUF per USD)",
                min_value=0.0001,
                value=float(st.session_state.get("parity_forward", default_spot)),
                step=0.01,
                key="parity_forward",
            )
        )
        tenor_label = st.selectbox(
            "Tenor",
            TENOR_LADDER,
            index=TENOR_LADDER.index(st.session_state.get("parity_tenor", "1Y")),
            key="parity_tenor",
        )
    with right:
        usd_rate_pct = float(
            st.number_input(
                "USD rate (%)",
                value=float(st.session_state.get("parity_usd_rate_pct", default_usd)),
                step=0.05,
                key="parity_usd_rate_pct",
            )
        )
        huf_rate_pct = float(
            st.number_input(
                "HUF rate (%)",
                value=float(st.session_state.get("parity_huf_rate_pct", default_huf)),
                step=0.05,
                key="parity_huf_rate_pct",
            )
        )

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

    learning_hint(
        "Compare the two forward curves above. Where they diverge most is where basis "
        "pressure is greatest. Ask yourself: is the wedge driven by rate differentials, "
        "FX supply-demand, or balance-sheet constraints?"
    )

    # --- Calculation windows ---
    calc_windows = {
        "theoretical_forward": CalculationWindow(
            "Theoretical forward",
            r"F_{CIP}=S\frac{1+r_{HUF}T}{1+r_{USD}T}",
            f"$S={spot:.4f}, r_{{HUF}}={huf_rate:.4%}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$",
            sign_convention_notes=("Higher HUF rate lifts HUF-per-USD forward.",),
            result=f"{breakdown['cip_implied_forward']:.4f}",
            expanded=True,
        ),
        "implied_huf_rate": CalculationWindow(
            "Implied HUF rate",
            r"r_{HUF}^{impl}=\frac{(F/S)(1+r_{USD}T)-1}{T}",
            f"$F={observed_forward:.4f}, S={spot:.4f}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$",
            sign_convention_notes=("Above market HUF curve implies positive wedge.",),
            result=f"{breakdown['implied_huf_rate']:.4%}",
        ),
        "implied_usd_rate": CalculationWindow(
            "Implied USD rate",
            r"r_{USD}^{impl}=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}",
            f"$F={observed_forward:.4f}, S={spot:.4f}, r_{{HUF}}={huf_rate:.4%}, T={tenor_years:.2f}$",
            sign_convention_notes=("Higher implied USD means worse synthetic USD funding.",),
            result=f"{breakdown['implied_usd_rate']:.4%}",
        ),
        "raw_basis_wedge": CalculationWindow(
            "Raw basis wedge",
            r"\text{Wedge}_{bp}=(r_{HUF}^{impl}-r_{HUF})\times 10{,}000",
            f"$({breakdown['implied_huf_rate']:.6f}-{huf_rate:.6f})\times10,000$",
            sign_convention_notes=(
                "Positive = observed forward above no-basis CIP under HUF/USD convention.",
                "Negative = observed forward below no-basis CIP.",
            ),
            result=f"{breakdown['raw_basis_wedge_bp']:.2f} bp",
        ),
        "synthetic_funding_cost": CalculationWindow(
            "Synthetic funding cost",
            r"\text{Synthetic USD cost} \approx r_{USD}^{impl}",
            "Using implied USD rate from spot-forward parity decomposition.",
            result=f"{breakdown['implied_usd_rate']:.4%}",
        ),
        "friction_adjusted_arbitrage_band": CalculationWindow(
            "Friction-adjusted arbitrage band",
            r"\text{Net edge}=\text{Raw wedge}-\text{Frictions}",
            "Friction inputs are not modelled on this page; interpret raw wedge before costs.",
            result="See page 5",
        ),
        "hedged_pickup": CalculationWindow(
            "Hedged pickup",
            r"\text{Pickup}=\text{Carry}-\text{Hedge costs}",
            "Carry and hedge implementation are shown in page 6.",
            result="See page 6",
        ),
        "conversion_factor": CalculationWindow(
            "Conversion factor",
            r"CF=F/S",
            f"$CF={observed_forward:.4f}/{spot:.4f}$",
            result=f"{observed_forward / spot:.6f}",
        ),
        "stressed_vs_base_deltas": CalculationWindow(
            "Stressed vs base deltas",
            r"\Delta x = x_{stress}-x_{base}",
            "This page displays current-state decomposition only.",
            result="See page 7",
        ),
    }
    render_required_calculation_windows(calc_windows, default_expanded=False)

    # --- Pedagogical footer ---
    render_page_footer(2)


if __name__ == "__main__":
    render_page()
else:
    render_page()
