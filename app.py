"""Example Streamlit page wiring shared calculation windows."""

from __future__ import annotations

import streamlit as st

from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows


st.set_page_config(page_title="XCCY Basis Swap Calculator", layout="wide")
st.title("XCCY Basis Swap Calculator")
st.caption("Collapsible calculation windows with formulas, assumptions, and results.")

calculations = {
    "theoretical_forward": CalculationWindow(
        title="Theoretical forward",
        formula=r"F = S_0 \times \frac{(1+r_{USD} \cdot T)}{(1+r_{HUF} \cdot T)}",
        substituted_values=r"$S_0=360$, $r_{USD}=5.20\%$, $r_{HUF}=7.40\%$, $T=0.5$",
        sign_convention_notes=(
            "Positive rate differential means HUF discount to spot in this quote style.",
        ),
        assumptions=("Simple compounding for both curves over T.",),
        result="F = 356.10 HUF/USD",
    ),
    "implied_huf_rate": CalculationWindow(
        title="Implied HUF rate",
        formula=r"r_{HUF,imp} = \frac{S_0(1+r_{USD}T)}{FT}-\frac{1}{T}",
        substituted_values=r"$S_0=360$, $F=356.10$, $r_{USD}=5.20\%$, $T=0.5$",
        sign_convention_notes=("Rates are annualized ACT/360 equivalent for display.",),
        assumptions=("Forward quote is clean and executable.",),
        result="r_HUF,imp = 7.34%",
    ),
    "implied_usd_rate": CalculationWindow(
        title="Implied USD rate",
        formula=r"r_{USD,imp} = \frac{F(1+r_{HUF}T)}{S_0T}-\frac{1}{T}",
        substituted_values=r"$S_0=360$, $F=356.10$, $r_{HUF}=7.40\%$, $T=0.5$",
        sign_convention_notes=("USD borrowing shown as positive carry cost.",),
        assumptions=("No holiday stub adjustments.",),
        result="r_USD,imp = 5.28%",
    ),
    "raw_basis_wedge": CalculationWindow(
        title="Raw basis wedge",
        formula=r"w_{raw}=r_{HUF,imp}-r_{HUF,mkt}",
        substituted_values=r"$r_{HUF,imp}=7.34\%$, $r_{HUF,mkt}=7.40\%$",
        sign_convention_notes=("Negative wedge means synthetic funding is cheaper than cash.",),
        assumptions=("Market HUF curve is bootstrap-consistent.",),
        result="w_raw = -6 bps",
    ),
    "synthetic_funding_cost": CalculationWindow(
        title="Synthetic funding cost",
        formula=r"c_{syn}=r_{USD}+basis+fees",
        substituted_values=r"$r_{USD}=5.20\%$, basis=$-0.18\%$, fees=$0.04\%$",
        sign_convention_notes=("Basis paid is negative in this market convention.",),
        assumptions=("Execution fees scale linearly with notionals.",),
        result="c_syn = 5.06%",
    ),
    "friction_adjusted_arbitrage_band": CalculationWindow(
        title="Friction-adjusted arbitrage band",
        formula=r"band=[w_{raw}-\phi,\;w_{raw}+\phi]",
        substituted_values=r"$w_{raw}=-6$ bps, friction buffer $\phi=9$ bps",
        sign_convention_notes=("Band crossing required before signal is tradable.",),
        assumptions=("Friction includes bid/offer + expected slippage.",),
        result="Band = [-15 bps, +3 bps]",
    ),
    "hedged_pickup": CalculationWindow(
        title="Hedged pickup",
        formula=r"pickup = y_{asset}-c_{syn}",
        substituted_values=r"$y_{asset}=5.55\%$, $c_{syn}=5.06\%$",
        sign_convention_notes=("Positive pickup favors hedged carry allocation.",),
        assumptions=("Asset spread DV01 mismatch ignored.",),
        result="Pickup = +49 bps",
    ),
    "conversion_factor": CalculationWindow(
        title="Conversion factor",
        formula=r"CF = \frac{N_{HUF}}{N_{USD}\times S_0}",
        substituted_values=r"$N_{HUF}=3.60bn$, $N_{USD}=10mm$, $S_0=360$",
        sign_convention_notes=("Factor above 1 indicates HUF leg over-coverage.",),
        assumptions=("No notional exchange at maturity beyond scheduled FX conversion.",),
        result="CF = 1.0000",
    ),
    "stressed_vs_base_deltas": CalculationWindow(
        title="Stressed vs base deltas",
        formula=r"\Delta_{stress}=metric_{stress}-metric_{base}",
        substituted_values=r"Base pickup $=+49$ bps, stressed pickup $=+21$ bps",
        sign_convention_notes=("Negative delta means stress erodes edge.",),
        assumptions=("Stress scenario: +50 bps USD, +25 bps HUF, +8 bps fees.",),
        result="Stress delta = -28 bps",
        expanded=True,
    ),
}

render_required_calculation_windows(calculations)
