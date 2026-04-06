from __future__ import annotations

from typing import Any

import streamlit as st

from shared_page_helpers import render_page_footer, render_page_header
from src.analytics.conversion_factor import (
    conversion_factor_curve_aware,
    conversion_factor_simple,
    spread_translation_round_trip_bp,
    translate_spread_bp,
)
from src.analytics.hedging import (
    hedged_pickup_decomposition_bp,
    matched_vs_rolling_hedge_economics_bp,
    roll_cost_and_risk_proxy_bp,
)
from src.explainers.theory_panels import render_pedagogical_scaffold
from src.state.session_access import get_canonical_market_context
from streamlit_calc_helpers import (
    CalculationWindow,
    SignConventionContext,
    render_calculation_windows,
    render_shared_sign_convention,
)
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


REQUIRED_CALCULATION_WINDOWS: tuple[str, ...] = (
    "conversion_factor",
    "relative_forward_difference",
    "theoretical_forward",
    "hedged_pickup",
    "implied_usd_rate",
)


def _build_payload(
    session_state: dict[str, Any],
    *,
    hedge_method: str,
    basis_sign_mode: str,
    risk_aversion_multiplier: float,
    roll_volatility_bp: float,
    expected_roll_drift_bp: float,
    extra_friction_bp: float,
    usd_zero_rates: list[float],
    tenor_weight_multipliers: list[float],
) -> dict[str, Any]:
    context = get_canonical_market_context(session_state)
    base_summary = context["summary_1y"]["base"]

    spot = float(base_summary["spot_fx"])
    usd = float(base_summary["usd_rate"])
    huf = float(base_summary["huf_rate"])
    basis_bps = float(base_summary["basis_bps"])

    tenor_years = [0.5, 1.0, 2.0]
    fwd_1y = spot * (1 + huf) / (1 + usd)

    simple_cf_payload = conversion_factor_simple(spot, fwd_1y)
    simple_cf = float(simple_cf_payload["conversion_factor"])

    forward_curve = [spot * (1 + huf * tenor) / (1 + usd * tenor) for tenor in tenor_years]
    synthetic_discount_factors = [1.0 / (1.0 + zr * tenor) for zr, tenor in zip(usd_zero_rates, tenor_years)]

    curve_cf_payload = conversion_factor_curve_aware(
        spot_huf_per_usd=spot,
        forward_huf_per_usd_by_tenor=forward_curve,
        tenor_years=tenor_years,
        discount_factors=synthetic_discount_factors,
        accrual_factors=tenor_weight_multipliers,
    )
    curve_cf = float(curve_cf_payload["conversion_factor"])

    nominal_diff_bp = (huf - usd) * 10_000.0
    gross_pickup_bp = translate_spread_bp(nominal_diff_bp, curve_cf)
    round_trip = spread_translation_round_trip_bp(nominal_diff_bp, curve_cf, tolerance_bp=1e-6)

    basis_component_bp = abs(basis_bps)
    if basis_sign_mode == "plus":
        signed_basis_component_bp = basis_component_bp
        basis_rule_text = "+ Basis"
    else:
        signed_basis_component_bp = -basis_component_bp
        basis_rule_text = "- Basis"

    matched_cost_bp = 47.0
    expected_rolling_cost_bp = 35.0 + expected_roll_drift_bp

    roll_payload = roll_cost_and_risk_proxy_bp(
        current_roll_cost_bp=35.0,
        expected_roll_cost_bp=expected_rolling_cost_bp,
        roll_volatility_bp=roll_volatility_bp,
        horizon_years=1.0,
    )
    hedge_choice = matched_vs_rolling_hedge_economics_bp(
        matched_hedge_cost_bp=matched_cost_bp,
        expected_rolling_cost_bp=float(roll_payload["expected_roll_cost_bp"]),
        roll_risk_proxy_bp=float(roll_payload["roll_risk_proxy_bp"]),
        risk_aversion_multiplier=risk_aversion_multiplier,
    )

    method_rows = [
        {
            "method": "maturity-matched",
            "expected_cost_bp": float(hedge_choice["matched_cost_bp"]),
            "roll_risk_proxy_bp": 0.0,
            "risk_adjusted_cost_bp": float(hedge_choice["matched_cost_bp"]),
        },
        {
            "method": "rolling",
            "expected_cost_bp": float(hedge_choice["expected_rolling_cost_bp"]),
            "roll_risk_proxy_bp": float(hedge_choice["roll_risk_proxy_bp"]),
            "risk_adjusted_cost_bp": float(hedge_choice["risk_adjusted_rolling_cost_bp"]),
        },
    ]

    selected_row = next(row for row in method_rows if row["method"] == hedge_method)

    decomposition = hedged_pickup_decomposition_bp(
        gross_spread_pickup_bp=gross_pickup_bp,
        hedge_cost_bp=float(selected_row["risk_adjusted_cost_bp"]),
        basis_drag_bp=signed_basis_component_bp,
        extra_friction_bp=extra_friction_bp,
    )

    return {
        "spot": spot,
        "fwd_1y": fwd_1y,
        "basis_bps": basis_bps,
        "simple_cf": simple_cf,
        "curve_cf": curve_cf,
        "curve_cf_payload": curve_cf_payload,
        "nominal_diff_bp": nominal_diff_bp,
        "gross_pickup_bp": gross_pickup_bp,
        "round_trip": round_trip,
        "basis_rule_text": basis_rule_text,
        "basis_component_bp": signed_basis_component_bp,
        "method_rows": method_rows,
        "selected_method": hedge_method,
        "decomposition": decomposition,
        "hedge_choice": hedge_choice,
        "roll_payload": roll_payload,
        "inputs": {
            "risk_aversion_multiplier": risk_aversion_multiplier,
            "roll_volatility_bp": roll_volatility_bp,
            "expected_roll_drift_bp": expected_roll_drift_bp,
            "extra_friction_bp": extra_friction_bp,
            "usd_zero_rates": usd_zero_rates,
            "tenor_weight_multipliers": tenor_weight_multipliers,
            "tenor_years": tenor_years,
            "synthetic_discount_factors": synthetic_discount_factors,
            "forward_curve": forward_curve,
        },
    }


def render_page() -> None:
    st.set_page_config(page_title="6. Hedged pickup and hedge choice", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[5]

    render_page_header(5, "6. Hedged Pickup and Hedge Choice")
    render_pedagogical_scaffold(
        st,
        page_number=6,
        learning_path=LEARNING_PATH,
        quantitative_outputs=(
            "Simple and curve-aware conversion factors",
            "Gross spread translated into hedged quote space",
            "Side-by-side matched-vs-rolling hedge economics",
            "Risk-adjusted net hedged pickup",
        ),
        derivation_items=(
            ("Conversion-factor construction", "Compute F/S simple CF and annuity-weighted curve-aware CF."),
            (
                "Pickup decomposition",
                "Pickup = (ΔBond – ΔSwap) ± Basis, then subtract hedge implementation and frictions.",
            ),
            (
                "Hedge-choice rule",
                "Compare maturity-matched expected cost to rolling risk-adjusted cost C_roll + λ·σ_roll.",
            ),
        ),
    )

    st.subheader("Hedge and conversion-factor controls")
    hedge_method = st.selectbox("Hedge method", ["maturity-matched", "rolling"], index=0)
    basis_sign_mode = st.selectbox(
        "Basis sign in pickup formula",
        ["minus", "plus"],
        index=0,
        help="Use minus for long-basis drag, plus for short-basis benefit.",
    )
    risk_aversion_multiplier = st.slider("Risk aversion λ", min_value=0.0, max_value=2.0, value=0.6, step=0.1)

    roll_volatility_bp = st.slider("Rolling hedge volatility (bp)", 0.0, 60.0, 18.0, 1.0)
    expected_roll_drift_bp = st.slider("Expected roll drift (bp)", -20.0, 30.0, 5.0, 1.0)
    extra_friction_bp = st.slider("Extra friction (bp)", 0.0, 25.0, 8.0, 1.0)

    st.caption("Synthetic market discount-factor controls (used directly in curve-aware CF).")
    usd_zero_rates = [
        st.slider("USD zero rate 0.5Y", 0.0, 0.15, 0.05, 0.001),
        st.slider("USD zero rate 1.0Y", 0.0, 0.15, 0.05, 0.001),
        st.slider("USD zero rate 2.0Y", 0.0, 0.15, 0.05, 0.001),
    ]

    st.caption("Tenor weight multipliers (accrual factors) used in annuity weights.")
    tenor_weight_multipliers = [
        st.slider("Weight multiplier 0.5Y", 0.1, 3.0, 0.5, 0.1),
        st.slider("Weight multiplier 1.0Y", 0.1, 3.0, 0.5, 0.1),
        st.slider("Weight multiplier 2.0Y", 0.1, 3.0, 1.0, 0.1),
    ]

    payload = _build_payload(
        st.session_state,
        hedge_method=hedge_method,
        basis_sign_mode=basis_sign_mode,
        risk_aversion_multiplier=risk_aversion_multiplier,
        roll_volatility_bp=roll_volatility_bp,
        expected_roll_drift_bp=expected_roll_drift_bp,
        extra_friction_bp=extra_friction_bp,
        usd_zero_rates=usd_zero_rates,
        tenor_weight_multipliers=tenor_weight_multipliers,
    )

    decomp = payload["decomposition"]
    a, b, c, d = st.columns(4)
    a.metric("Simple CF (F/S)", f"{payload['simple_cf']:.6f}")
    b.metric("Curve-aware CF", f"{payload['curve_cf']:.6f}")
    c.metric("Translated gross", f"{payload['gross_pickup_bp']:.2f} bps")
    d.metric("Net hedged pickup", f"{decomp['net_hedged_pickup_bp']:.2f} bps")

    st.markdown("**Formula:** Pickup = (ΔBond – ΔSwap) ± Basis")
    st.caption(
        "Direction rule: use **+ Basis** when basis is a pickup tailwind for your position and "
        "**- Basis** when basis is a drag. "
        f"Current selection applies: **{payload['basis_rule_text']}**."
    )

    st.subheader("Hedge method economics (side-by-side)")
    st.dataframe(payload["method_rows"], use_container_width=True)
    st.caption(
        "Preferred on risk-adjusted cost basis: "
        f"**{str(payload['hedge_choice']['preferred_hedge']).replace('matched', 'maturity-matched')}**"
    )

    weights = payload["curve_cf_payload"]["components"]["weights"]
    input_block = payload["inputs"]
    st.write(
        {
            "tenor_years": input_block["tenor_years"],
            "synthetic_discount_factors": input_block["synthetic_discount_factors"],
            "annuity_weights": weights,
        }
    )

    round_trip = payload["round_trip"]
    sign_context = SignConventionContext(
        quote_convention="HUF per USD",
        perspective="Investor evaluating hedged pickup with explicit maturity-matched versus rolling choices.",
        positive_interpretation="Positive pickup means net economics remain favorable after selected hedge costs.",
        negative_interpretation="Negative pickup means hedge and basis effects dominate gross carry.",
    )
    render_shared_sign_convention(sign_context)

    render_calculation_windows(
        [
            CalculationWindow(
                title="Simple conversion factor",
                meaning="Direct quote-space conversion from 1Y forward over spot.",
                significance="Baseline mapping from HUF-bp into USD-bp.",
                formula=r"CF_{simple}=F/S",
                methodology="Compute forward divided by spot at matched tenor.",
                inputs="1Y forward and spot in HUF per USD.",
                substituted_values=f"$F={payload['fwd_1y']:.4f}, S={payload['spot']:.4f}$",
                derivation_steps=("Collect matched tenor F and S.", "Divide F by S.",),
                assumptions=("Single-tenor approximation.",),
                interpretation="Useful quick check before curve-aware weighting.",
                common_misunderstandings=("Treating simple CF as maturity-invariant.",),
                result=f"{payload['simple_cf']:.6f}",
            ),
            CalculationWindow(
                title="Curve-aware conversion factor",
                meaning="Annuity-weighted conversion factor across tenors.",
                significance="Ties conversion to synthetic market discount factors and tenor weights.",
                formula=r"CF_{curve}=\sum_i w_i(F_i/S)",
                methodology="Derive discount-factor annuity weights and apply them to tenor forward ratios.",
                inputs="Spot, tenor forwards, synthetic discount factors, and tenor weight multipliers.",
                substituted_values=(
                    f"$DF={input_block['synthetic_discount_factors']}, w={weights}$"
                ),
                derivation_steps=("Compute annuity terms DF_i·Δ_i.", "Normalize to weights w_i.", "Sum weighted F_i/S ratios.",),
                assumptions=("Synthetic USD curve proxies the funding term structure.",),
                interpretation="Shows how curve shape and weighting alter spread translation.",
                common_misunderstandings=("Ignoring tenor weights when exposure spans maturities.",),
                result=f"{payload['curve_cf']:.6f}",
            ),
            CalculationWindow(
                title="Spread translation round-trip",
                meaning="Checks conversion consistency by translating out and back.",
                significance="Confirms unit discipline and numerical stability.",
                formula=r"\text{HUF bp}\rightarrow\text{USD bp}\rightarrow\text{HUF bp}",
                methodology="Apply CF forward and inverse and compute residual.",
                inputs="Input HUF spread and curve-aware conversion factor.",
                substituted_values=(
                    f"${round_trip['huf_bp_in']:.2f}\to{round_trip['usd_bp_translated']:.2f}"
                    f"\to{round_trip['huf_bp_round_trip']:.2f}$"
                ),
                derivation_steps=("Translate HUF to USD.", "Translate USD back to HUF.", "Measure residual.",),
                assumptions=("Same convention for forward and inverse translation.",),
                interpretation="Residual near zero indicates coherent translation logic.",
                common_misunderstandings=("Skipping round-trip checks after changing CF controls.",),
                result=f"residual={round_trip['round_trip_residual_bp']:.6f} bp",
            ),
            CalculationWindow(
                title="Hedge method comparison",
                meaning="Compares maturity-matched and rolling economics side by side.",
                significance="Separates expected cost from roll risk and risk-adjusted cost.",
                formula=r"C_{roll,RA}=C_{roll,exp}+\lambda\sigma_{roll}",
                methodology="Compute rolling risk-adjusted cost and compare against matched expected cost.",
                inputs="Matched expected cost, rolling expected cost, roll-risk proxy, risk aversion λ.",
                substituted_values=(
                    f"$C_m={payload['hedge_choice']['matched_cost_bp']:.2f}, "
                    f"C_r={payload['hedge_choice']['expected_rolling_cost_bp']:.2f}, "
                    f"\\sigma={payload['hedge_choice']['roll_risk_proxy_bp']:.2f}, "
                    f"\\lambda={payload['hedge_choice']['risk_aversion_multiplier']:.2f}$"
                ),
                derivation_steps=("Compute C_roll,RA.", "Compare against C_m.", "Choose lower risk-adjusted cost method.",),
                assumptions=("Roll-risk proxy scales with sqrt-time.",),
                interpretation="Preference can flip as roll risk or risk aversion rises.",
                common_misunderstandings=("Comparing methods using only expected carry.",),
                result=f"preferred={payload['hedge_choice']['preferred_hedge']}",
            ),
            CalculationWindow(
                title="Pickup decomposition",
                meaning="Final risk-adjusted pickup under selected hedge method.",
                significance="Turns gross translated spread into executable net pickup.",
                formula=r"\text{Pickup}=(\Delta Bond-\Delta Swap)\pm Basis-Hedge-Extra",
                methodology="Apply signed basis rule, then subtract selected hedge cost and extra friction.",
                inputs="Gross pickup, selected hedge-method risk-adjusted cost, signed basis, extra friction.",
                substituted_values=(
                    f"${decomp['gross_pickup_bp']:.2f}-{decomp['hedge_cost_bp']:.2f}"
                    f"{payload['basis_rule_text'].replace('Basis', str(abs(payload['basis_component_bp'])))}"
                    f"-{decomp['extra_friction_bp']:.2f}$"
                ),
                derivation_steps=("Translate nominal differential using CF.", "Apply basis sign rule.", "Subtract hedge and frictions.",),
                assumptions=("Basis sign follows trade direction rule selected above.",),
                interpretation="Positive net pickup indicates the selected hedge method preserves carry.",
                common_misunderstandings=("Using wrong basis sign for trade direction.",),
                result=f"{decomp['net_hedged_pickup_bp']:.2f} bps",
            ),
        ],
        sign_convention=sign_context,
    )

    learning_hint(
        "Watch how risk-adjusted rolling cost rises with roll volatility and can flip method preference "
        "from rolling to maturity-matched."
    )
    render_page_footer(5)


if __name__ == "__main__":
    render_page()
else:
    render_page()
