from __future__ import annotations

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.xccy_swap import SwapPeriod, cashflow_timeline, synthetic_funding_cost_outputs
from src.explainers.theory_panels import render_pedagogical_scaffold
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "theoretical_forward",
    "implied_usd_rate",
    "synthetic_funding_cost",
)


def render_page() -> None:
    from streamlit_calc_helpers import (
        SignConventionContext,
        render_shared_sign_convention,
    )

    st.set_page_config(page_title="2. XCCY mechanics", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[1]

    context = get_canonical_market_context(st.session_state)
    summary = context["summary_1y"]["base"]

    spot = float(summary["spot_fx"])
    usd_rate = float(summary["usd_rate"])
    huf_rate = float(summary["huf_rate"])
    basis = float(summary["basis_bps"]) / 10_000.0

    timeline = cashflow_timeline(10_000_000, spot, [SwapPeriod("1Y", 1.0, usd_rate, huf_rate)], basis)
    forward = spot * (1 + (huf_rate + basis)) / (1 + usd_rate)
    out = synthetic_funding_cost_outputs(spot, forward, huf_rate, basis, 1.0)

    # --- Header with learning objectives ---
    render_page_header(1, "2. XCCY Mechanics")

    # --- Metrics ---
    st.title("2. XCCY mechanics")
    render_pedagogical_scaffold(
        st,
        page_number=2,
        learning_path=LEARNING_PATH,
        quantitative_outputs=("Spot", "Basis (bps)", "Basis drag (bp)", "USD-leg cashflow timeline table"),
        derivation_items=(
            (
                "Synthetic USD (no basis): derivation",
                "Start from CIP with b=0 and solve for implied USD funding from spot, forward, and HUF rate.",
            ),
            (
                "Synthetic USD (with basis): derivation",
                "Add basis b to the HUF leg coupon before converting through forward/spot.",
            ),
            (
                "Basis drag: derivation",
                "Compute synthetic-with-basis minus synthetic-without-basis, then convert to basis points.",
            ),
        ),
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Spot", f"{spot:.4f}")
    c2.metric("Basis", f"{basis * 10_000:.1f} bps")
    c3.metric("Basis drag", f"{out['basis_drag_bp']:.2f} bps")

    # --- Cashflow timeline ---
    st.markdown("### Cashflow Timeline")
    st.bar_chart(
        {"date": [x["date"] for x in timeline], "usd": [x["usd_cashflow"] for x in timeline]},
        x="date",
    )
    st.dataframe(timeline, use_container_width=True)

    st.markdown(
        "Mechanics are shown from the **USD-receiver / HUF-payer** perspective. "
        "Positive cashflows are received by the USD leg receiver."
    )

    learning_hint(
        "Focus on how the basis spread modifies the HUF leg coupon. The basis drag metric "
        "tells you exactly how many bps of extra cost the basis adds to synthetic funding. "
        "Try changing the scenario to see how stress widens this drag."
    )

    # --- Calculation windows ---
    render_calculation_windows(
        [
            CalculationWindow(
                "Synthetic USD (no basis)",
                r"r=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}",
                f"$S={spot:.4f}, F={forward:.4f}, r_{{HUF}}={huf_rate:.4%}$",
                ("Positive rate = higher funding cost.",),
                result=f"{out['synthetic_usd_rate_no_basis']:.4%}",
            ),
            CalculationWindow(
                "Synthetic USD (with basis)",
                r"r=\frac{\frac{1+(r_{HUF}+b)T}{F/S}-1}{T}",
                f"$b={basis:.4%}$",
                ("Positive basis increases HUF coupon.",),
                result=f"{out['synthetic_usd_rate_with_basis']:.4%}",
            ),
            CalculationWindow(
                "Basis drag",
                r"(r_{with}-r_{no})\times 10{,}000",
                f"$({out['synthetic_usd_rate_with_basis']:.6f}-{out['synthetic_usd_rate_no_basis']:.6f})\times10,000$",
                ("Positive drag means worse synthetic funding.",),
                result=f"{out['basis_drag_bp']:.2f} bp",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(1)
    st.write("Mechanics are shown from the USD-receiver / HUF-payer perspective.")
    learning_hint("Positive cashflows are received by the USD leg receiver.")
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="USD-receiver / HUF-payer swap leg direction.",
        positive_interpretation="Positive metric implies higher USD-side synthetic cost or inflow for the stated leg.",
        negative_interpretation="Negative metric implies lower USD-side synthetic cost or outflow for the stated leg.",
    )
    render_shared_sign_convention(sign_context)
    render_calculation_windows([
        CalculationWindow(
            title="Synthetic USD (no basis)",
            concept_meaning="Implied USD funding rate from spot-forward parity excluding basis.",
            why_it_matters="This is the benchmark synthetic USD cost before basis distortions.",
            formula=r"r=\frac{\frac{1+r_{HUF}T}{F/S}-1}{T}",
            methodology_rationale="Invert CIP to recover the USD-equivalent funding rate.",
            inputs_used=f"Spot/forward in HUF per USD, r_HUF={huf_rate:.4%}, tenor=1Y.",
            substituted_values=f"$S={spot:.4f}, F={forward:.4f}, r_{{HUF}}={huf_rate:.4%}$",
            derivation_steps=("Compute F/S.", "Apply parity inversion.", "Annualize over T=1."),
            assumptions=("Simple annual compounding.",),
            interpretation="Higher implied rate means more expensive synthetic USD borrowing.",
            common_misunderstandings=("Ignoring quote convention can flip sign interpretation.",),
            result=f"{out['synthetic_usd_rate_no_basis']:.4%}",
        ),
        CalculationWindow(
            title="Synthetic USD (with basis)",
            concept_meaning="Implied USD funding rate after adding cross-currency basis to HUF leg.",
            why_it_matters="Shows the all-in synthetic USD funding cost faced in market quotes.",
            formula=r"r=\frac{\frac{1+(r_{HUF}+b)T}{F/S}-1}{T}",
            methodology_rationale="Basis shifts the HUF coupon used in parity reconstruction.",
            inputs_used=f"Same as above plus basis b={basis:.4%}.",
            substituted_values=f"$b={basis:.4%}$",
            derivation_steps=("Shift HUF rate by b.", "Recompute implied USD rate.", "Compare with no-basis case."),
            assumptions=("Basis is applied additively to the HUF leg.",),
            interpretation="Positive basis increases synthetic USD cost in this setup.",
            common_misunderstandings=("Treating basis as independent of forward pricing.",),
            result=f"{out['synthetic_usd_rate_with_basis']:.4%}",
        ),
        CalculationWindow(
            title="Basis drag",
            concept_meaning="Incremental funding penalty from including basis.",
            why_it_matters="Quantifies basis impact directly in basis points.",
            formula=r"(r_{with}-r_{no})\times 10{,}000",
            methodology_rationale="Take the difference between with/without-basis implied rates.",
            inputs_used="Implied USD rates from previous two windows.",
            substituted_values=f"$({out['synthetic_usd_rate_with_basis']:.6f}-{out['synthetic_usd_rate_no_basis']:.6f})\\times10,000$",
            derivation_steps=("Subtract implied rates.", "Convert decimal rate difference to bps.",),
            assumptions=("Both rates measured on the same tenor and compounding basis.",),
            interpretation="Positive drag means worse synthetic funding.",
            common_misunderstandings=("Confusing basis drag with outright level of USD rates.",),
            result=f"{out['basis_drag_bp']:.2f} bp",
        ),
    ])


if __name__ == "__main__":
    render_page()
else:
    render_page()
