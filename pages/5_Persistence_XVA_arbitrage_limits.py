from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.frictions import (
    deposit_adjusted_arbitrage_band_bp,
    friction_adjusted_arbitrage_band_bp,
)
from src.explainers.theory_panels import render_pedagogical_scaffold
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "friction_adjusted_arbitrage_band",
    "forward_difference",
    "raw_basis_wedge",
)


def render_page() -> None:
    from streamlit_calc_helpers import SignConventionContext, render_shared_sign_convention

    st.set_page_config(page_title="5. Persistence / XVA / arbitrage limits", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[4]
    st.title("5. Persistence / XVA / arbitrage limits")

    render_pedagogical_scaffold(
        st,
        page_number=5,
        learning_path=LEARNING_PATH,
        quantitative_outputs=(
            "Raw edge (bp)",
            "Total friction band (bp)",
            "Deposit + XVA + capital adjustment (bp)",
            "Actionability flag",
        ),
        derivation_items=(
            ("Model friction", "Compute operational frictions (funding, clearing, liquidity, capacity)."),
            ("Overlay friction", "Add explicit deposit borrowing, CVA, FVA, and capital overlays."),
            ("Executable edge", "Apply shared sign convention to convert apparent wedge into net edge."),
        ),
    )

    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
    raw = float(summary["basis_bps"])

    st.markdown("### Explicit Deposit / XVA / Capital Inputs (bps)")
    c1, c2, c3, c4 = st.columns(4)
    deposit_borrowing_bp = c1.number_input("Deposit-spread component", min_value=0.0, value=18.0, step=0.5)
    cva_overlay_bp = c2.number_input("CVA overlay", min_value=0.0, value=4.0, step=0.5)
    fva_overlay_bp = c3.number_input("FVA overlay", min_value=0.0, value=3.0, step=0.5)
    capital_overlay_bp = c4.number_input("Capital charge overlay", min_value=0.0, value=3.0, step=0.5)

    # Existing model output components (kept explicit so users can see what gets overlaid).
    funding_spread_bp, clearing_friction_bp, liquidity_repo_friction_bp = 6.0, 2.0, 5.0

    rows = []
    for cap in [0.8, 1.0, 1.2, 1.5]:
        model = friction_adjusted_arbitrage_band_bp(
            raw_basis_edge_bp=raw,
            capital_charge_bp=0.0,
            funding_spread_bp=funding_spread_bp,
            cva_proxy_bp=0.0,
            fva_proxy_bp=0.0,
            clearing_friction_bp=clearing_friction_bp,
            liquidity_repo_friction_bp=liquidity_repo_friction_bp,
            counterparty_quality_multiplier=1.0,
            capacity_multiplier=cap,
        )
        overlay = deposit_adjusted_arbitrage_band_bp(
            raw_basis_edge_bp=raw,
            base_friction_bp=float(model["total_friction_bp"]),
            deposit_borrowing_bp=deposit_borrowing_bp,
            cva_bp=cva_overlay_bp,
            fva_bp=fva_overlay_bp,
            capital_charge_bp=capital_overlay_bp,
        )
        rows.append(
            {
                "capacity": cap,
                "raw_edge_bp": raw,
                "model_friction_bp": float(model["total_friction_bp"]),
                "overlay_friction_bp": float(overlay["overlay_friction_bp"]),
                "total_friction_bp": float(overlay["total_friction_bp"]),
                "net_edge_bp": float(overlay["net_edge_bp"]),
                "upper_band_bp": float(overlay["total_friction_bp"]),
                "lower_band_bp": -float(overlay["total_friction_bp"]),
                "is_actionable": bool(overlay["is_actionable"]),
            }
        )
    base = next(r for r in rows if r["capacity"] == 1.0)

    render_page_header(4, "5. Persistence / XVA / Arbitrage Limits")

    a, b, c = st.columns(3)
    a.metric("Raw wedge", f"{base['raw_edge_bp']:.2f} bps")
    b.metric("Total friction band", f"{base['total_friction_bp']:.2f} bps")
    c.metric("Executable?", "Yes" if base["is_actionable"] else "No")

    st.markdown("### Apparent Arbitrage vs Executable Arbitrage")
    apparent_col, execute_col = st.columns(2)
    apparent_col.markdown(
        f"""
- **Raw wedge:** {base['raw_edge_bp']:.2f} bp
- **Deposit borrowing adjustment:** -{deposit_borrowing_bp:.2f} bp
- **XVA/capital adjustments (CVA + FVA + capital):** -{(cva_overlay_bp + fva_overlay_bp + capital_overlay_bp):.2f} bp
- **Resulting net edge (after all frictions):** {base['net_edge_bp']:.2f} bp
"""
    )
    execute_col.dataframe(
        {
            "Component": ["Model friction", "Deposit borrowing", "CVA", "FVA", "Capital", "Total friction"],
            "bps": [
                base["model_friction_bp"],
                deposit_borrowing_bp,
                cva_overlay_bp,
                fva_overlay_bp,
                capital_overlay_bp,
                base["total_friction_bp"],
            ],
        },
        hide_index=True,
        use_container_width=True,
    )

    st.info(
        "**Rookie-trader caution:** a headline 33-pip wedge can look compelling, but once funding/deposit drag "
        "and XVA/capital costs are layered in, the net edge can flip to roughly **-28 bp** or worse. "
        "Always convert apparent arbitrage into executable arbitrage before trading."
    )

    st.markdown("### Net Edge vs Friction Band Across Capacity")
    st.line_chart(
        {
            "capacity": [r["capacity"] for r in rows],
            "net_edge": [r["net_edge_bp"] for r in rows],
            "friction_band": [r["upper_band_bp"] for r in rows],
        },
        x="capacity",
    )
    st.dataframe(rows, use_container_width=True)

    learning_hint(
        "Persistence puzzle intuition: apparent wedges survive when implementation frictions absorb them. "
        "Deposit borrowing + XVA/capital overlays often decide whether a trade is truly executable."
    )

    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Arbitrageur converting a raw wedge into executable edge after deposit/XVA/capital costs.",
        positive_interpretation="Positive raw/net edge favors the quoted-direction trade.",
        negative_interpretation="Negative raw/net edge favors the mirror direction.",
    )
    render_shared_sign_convention(sign_context)

    render_calculation_windows(
        [
            CalculationWindow(
                title="Total friction with overlays",
                meaning="Model friction plus explicit deposit borrowing, CVA, FVA, and capital overlays.",
                significance="Defines the executable no-trade band around apparent arbitrage.",
                formula=r"F_{total}=F_{model}+d_{dep}+c_{CVA}+c_{FVA}+c_{cap}",
                methodology="Compute model friction from the existing stack, then add explicit overlays.",
                inputs="Model friction and four overlay inputs (bps).",
                substituted_values=(
                    f"${base['model_friction_bp']:.2f}+{deposit_borrowing_bp:.2f}+{cva_overlay_bp:.2f}"
                    f"+{fva_overlay_bp:.2f}+{capital_overlay_bp:.2f}$"
                ),
                derivation_steps=("Compute base model friction.", "Add deposit/XVA/capital overlays."),
                assumptions=("All overlays are additive implementation costs.",),
                interpretation="Higher overlays widen the persistence band and reduce tradable edge.",
                common_misunderstandings=("Treating raw wedge as executable without funding/XVA erosion.",),
                result=f"{base['total_friction_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Net executable edge",
                meaning="Directional net edge after total friction while preserving sign convention.",
                significance="Shows whether apparent arbitrage survives implementation costs.",
                formula=r"\text{Net} = \text{Raw} - \operatorname{sign}(\text{Raw})\times F_{total}",
                methodology="Apply directional sign logic to friction-adjusted edge.",
                inputs="Raw wedge and total friction (bps).",
                substituted_values=f"${base['raw_edge_bp']:.2f} \rightarrow {base['net_edge_bp']:.2f}$",
                derivation_steps=("Use raw-edge sign.", "Apply total friction in the cost direction."),
                assumptions=("Execution follows the shared sign convention context.",),
                interpretation="Positive means executable edge remains; negative means mirror side dominates.",
                common_misunderstandings=("Ignoring direction when applying costs.",),
                result=f"{base['net_edge_bp']:.2f} bps",
            ),
        ]
    )

    render_page_footer(4)


if __name__ == "__main__":
    render_page()
else:
    render_page()
