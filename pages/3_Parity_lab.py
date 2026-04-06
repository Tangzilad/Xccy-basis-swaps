from __future__ import annotations

from src.state.session_access import get_canonical_market_context
from src.analytics.parity import parity_decomposition, tenor_ladder_decomposition, tenor_to_year_fraction


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


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _from_decimal(v: float) -> float:
    return v * 100.0 if v < 1 else v


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="3. Parity lab", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[2]

    st.title("3. Parity lab")
    a, b, c = st.columns(3)
    a.metric("Observed 1Y", f"{one['observed_forward']:.4f}")
    b.metric("Fair 1Y", f"{one['fair_forward_no_basis']:.4f}")
    c.metric("Raw wedge", f"{one['raw_basis_wedge_bp']:.2f} bps")
    st.line_chart({"tenor": [r["tenor"] for r in rows], "wedge": [r["raw_basis_wedge_bp"] for r in rows]}, x="tenor")
    st.dataframe(rows, use_container_width=True)
    st.write("Observed forwards are benchmarked versus no-basis CIP fair values.")
    context = get_canonical_market_context(st.session_state)
    base_summary = context["summary_1y"]["base"]
    default_spot = float(base_summary["spot_fx"])
    default_usd = _from_decimal(float(base_summary["usd_rate"]))
    default_huf = _from_decimal(float(base_summary["huf_rate"]))

    button = getattr(st, "button", None)
    st.subheader("Canonical inputs")
    if callable(button) and button("Worked example (HUF/USD)"):
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

    st.subheader("Decomposition outputs")
    c1, c2, c3 = st.columns(3)
    c1.metric("CIP-implied forward", f"{breakdown['cip_implied_forward']:.4f}")
    c2.metric("Implied HUF rate", f"{breakdown['implied_huf_rate']:.4%}")
    c3.metric("Implied USD rate", f"{breakdown['implied_usd_rate']:.4%}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Forward difference", f"{breakdown['forward_difference']:.4f}")
    c5.metric("Relative forward diff", f"{breakdown['forward_relative_bp']:.2f} bp")
    c6.metric("Raw basis wedge", f"{breakdown['raw_basis_wedge_bp']:.2f} bp")

    sign_convention_text = (
        "**Sign convention (HUF per USD):** "
        "A **positive** raw basis wedge means the observed forward is high vs no-basis CIP, "
        "so implied HUF funding is richer (worse for synthetic USD borrowing via HUF). "
        "A **negative** wedge means observed forward is low vs CIP and synthetic USD funding is cheaper."
    )
    st.markdown(sign_convention_text)

    ladder = tenor_ladder_decomposition(
        spot_huf_per_usd=spot,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        tenor_labels=TENOR_LADDER,
        anchor_observed_forward=observed_forward,
        anchor_tenor_label=tenor_label,
    )

    st.subheader("Tenor ladder")
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

    learning_hint("Persistent wedge signals parity stress.")

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
        "forward_difference": CalculationWindow(
            "Forward difference",
            r"\Delta F=F_{obs}-F_{CIP}",
            f"${observed_forward:.4f}-{breakdown['cip_implied_forward']:.4f}$",
            result=f"{breakdown['forward_difference']:.4f}",
        ),
        "relative_forward_difference": CalculationWindow(
            "Relative forward difference",
            r"\text{RelDiff}_{bp}=\left(\frac{F_{obs}}{F_{CIP}}-1\right)\times10{,}000",
            f"$({observed_forward:.6f}/{breakdown['cip_implied_forward']:.6f}-1)\\times10,000$",
            result=f"{breakdown['forward_relative_bp']:.2f} bp",
        ),
    }
    st.subheader("Calculation windows")
    render_required_calculation_windows(
        calc_windows,
        required_keys=REQUIRED_CALCULATION_WINDOWS,
        page_name="3. Parity lab",
        default_expanded=False,
    )


if __name__ == "__main__":
    render_page()
else:
    render_page()
