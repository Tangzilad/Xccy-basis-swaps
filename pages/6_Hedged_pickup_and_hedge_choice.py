from __future__ import annotations

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
from src.state.session_access import get_canonical_market_context


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="6. Hedged pickup and hedge choice", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[5]

    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
    spot, usd, huf, basis = float(summary["spot_fx"]), float(summary["usd_rate"]), float(summary["huf_rate"]), float(summary["basis_bps"])

    fwd = spot * (1 + huf) / (1 + usd)
    cf = conversion_factor_from_fx(spot, fwd)
    gross = translate_spread_bp((huf - usd) * 10_000, cf)

    rows = []
    for hc in [20.0, 35.0, 50.0]:
        rp = roll_cost_and_risk_proxy_bp(hc, hc + 5.0, 18.0, 1.0)
        ch = matched_vs_rolling_hedge_economics_bp(hc + 12.0, hc, rp["roll_risk_proxy_bp"], 0.6)
        rows.append({"hedge_cost": hc, "pickup": hedged_pickup_bp(gross, hc, abs(basis), 8.0), **rp, **ch})
    base = next(r for r in rows if r["hedge_cost"] == 35.0)

    st.title("6. Hedged pickup and hedge choice")
    a, b, c = st.columns(3)
    a.metric("Converted gross", f"{gross:.2f} bps")
    b.metric("Net pickup", f"{base['pickup']:.2f} bps")
    c.metric("Preferred", str(base["preferred_hedge"]).title())
    st.line_chart({"hedge_cost": [r['hedge_cost'] for r in rows], "pickup": [r['pickup'] for r in rows], "benefit_of_rolling": [r['benefit_of_rolling_bp'] for r in rows]}, x="hedge_cost")
    st.dataframe(rows, use_container_width=True)
    render_global_shell(); st.session_state.suggested_page = LEARNING_PATH[5]
    context = get_canonical_market_context(st.session_state)
    base_summary = context["summary_1y"]["base"]
    spot = float(base_summary["spot_fx"])
    usd = float(base_summary["usd_rate"])
    huf = float(base_summary["huf_rate"])
    basis = float(base_summary["basis_bps"])
    fwd=spot*(1+huf)/(1+usd)
    simple_cf_payload = conversion_factor_simple(spot, fwd)
    simple_cf = float(simple_cf_payload["conversion_factor"])

    tenor_years = [0.5, 1.0, 2.0]
    forward_curve = [spot * (1 + huf * t) / (1 + usd * t) for t in tenor_years]
    discount_factors = [1 / (1 + usd * t) for t in tenor_years]
    curve_cf_payload = conversion_factor_curve_aware(
        spot_huf_per_usd=spot,
        forward_huf_per_usd_by_tenor=forward_curve,
        tenor_years=tenor_years,
        discount_factors=discount_factors,
    )
    curve_cf = float(curve_cf_payload["conversion_factor"])

    nominal_diff_bp = (huf - usd) * 10_000
    gross_pickup_bp = translate_spread_bp(nominal_diff_bp, curve_cf)
    round_trip = spread_translation_round_trip_bp(nominal_diff_bp, curve_cf, tolerance_bp=1e-6)

    rows = []
    for hedge_cost_bp in [20.0, 35.0, 50.0]:
        roll_payload = roll_cost_and_risk_proxy_bp(
            current_roll_cost_bp=hedge_cost_bp,
            expected_roll_cost_bp=hedge_cost_bp + 5.0,
            roll_volatility_bp=18.0,
            horizon_years=1.0,
        )
        hedge_choice_payload = matched_vs_rolling_hedge_economics_bp(
            matched_hedge_cost_bp=hedge_cost_bp + 12.0,
            expected_rolling_cost_bp=hedge_cost_bp,
            roll_risk_proxy_bp=roll_payload["roll_risk_proxy_bp"],
            risk_aversion_multiplier=0.6,
        )
        decomposition = hedged_pickup_decomposition_bp(
            gross_spread_pickup_bp=gross_pickup_bp,
            hedge_cost_bp=hedge_cost_bp,
            basis_drag_bp=abs(basis),
            extra_friction_bp=8.0,
        )
        rows.append(
            {
                "hedge_cost": hedge_cost_bp,
                "pickup": decomposition["net_hedged_pickup_bp"],
                **decomposition,
                **roll_payload,
                **hedge_choice_payload,
            }
        )

    base = next(row for row in rows if row["hedge_cost"] == 35.0)
    return {
        "spot": spot,
        "usd": usd,
        "huf": huf,
        "basis": basis,
        "fwd_1y": fwd_1y,
        "nominal_diff_bp": nominal_diff_bp,
        "simple_cf_payload": simple_cf_payload,
        "simple_cf": simple_cf,
        "curve_cf_payload": curve_cf_payload,
        "curve_cf": curve_cf,
        "round_trip": round_trip,
        "gross_pickup_bp": gross_pickup_bp,
        "rows": rows,
        "base": base,
    }


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="6. Hedged pickup and hedge choice", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[5]

    payload = _build_canonical_payload(_get_market_state(st.session_state))

    st.title("6. Hedged pickup and hedge choice")
    a, b, c, d = st.columns(4)
    a.metric("Simple CF (F/S)", f"{payload['simple_cf']:.6f}")
    b.metric("Curve-aware CF", f"{payload['curve_cf']:.6f}")
    c.metric("Converted gross", f"{payload['gross_pickup_bp']:.2f} bps")
    d.metric("Net pickup", f"{payload['base']['pickup']:.2f} bps")
    st.caption(f"Preferred hedge method (base case): **{str(payload['base']['preferred_hedge']).title()}**")

    st.line_chart(
        {
            "hedge_cost": [row["hedge_cost"] for row in payload["rows"]],
            "pickup": [row["pickup"] for row in payload["rows"]],
            "benefit_of_rolling": [row["benefit_of_rolling_bp"] for row in payload["rows"]],
        },
        x="hedge_cost",
    )
    st.dataframe(payload["rows"], use_container_width=True)
    st.write("Hedge choice is based on risk-adjusted pickup rather than carry alone.")
    st.markdown(
        """
        **Why CF is not “just FX”:** the conversion factor is the map from one quote space (HUF-bp) into another
        (USD-bp). Spot alone does not control that map—forward points and curve weights matter, which is why the
        curve-aware CF can differ from the simple (F/S) ratio.

        **Why hedged pickup differs from nominal yield differential:** the nominal HUF-USD differential is only a
        starting point. Realized hedged pickup subtracts hedge implementation cost, basis drag, and frictions.
        Therefore “higher nominal yield” can still produce weak or negative net pickup after hedging.
        """
    )
    learning_hint("Rolling hedges can lose after volatility-scaled roll risk penalties.")

    base = payload["base"]
    round_trip = payload["round_trip"]
    render_calculation_windows(
        [
            CalculationWindow(
                title="Simple conversion factor",
                concept_meaning="Direct quote-space conversion ratio between forward and spot.",
                why_it_matters="Provides a fast translation between HUF-bp and USD-bp scales.",
                formula=r"CF_{simple}=F/S",
                methodology_rationale="Use tenor-matched forward divided by spot.",
                inputs_used="1Y forward and spot, both in HUF per USD.",
                substituted_values=f"$F={payload['fwd_1y']:.4f}, S={payload['spot']:.4f}$",
                derivation_steps=("Take forward/spot ratio.",),
                assumptions=("Single-tenor approximation.",),
                interpretation="Higher CF maps a given HUF spread into a larger USD spread.",
                common_misunderstandings=("Assuming spot alone determines conversion.",),
                result=f"{payload['simple_cf']:.6f}",
            ),
            CalculationWindow(
                title="Curve-aware conversion factor",
                concept_meaning="Weighted conversion factor across tenor buckets.",
                why_it_matters="Improves translation accuracy when carry lives across the curve.",
                formula=r"CF_{curve}=\sum_i w_i(F_i/S)",
                methodology_rationale="Apply annuity-style weights to tenor-specific forward ratios.",
                inputs_used="Spot plus tenor ladder forwards and normalized weights.",
                substituted_values=f"$\\sum_i w_i=1, S={payload['spot']:.4f}$",
                derivation_steps=("Compute F_i/S for each tenor.", "Weight by w_i.", "Sum across tenors.",),
                assumptions=("Weights represent relevant exposure profile.",),
                interpretation="Divergence from simple CF indicates curve-shape effects.",
                common_misunderstandings=("Treating conversion as a constant across maturities.",),
                result=f"{payload['curve_cf']:.6f}",
            ),
            CalculationWindow(
                title="Spread translation round-trip",
                concept_meaning="Consistency check for conversion-factor mapping.",
                why_it_matters="Verifies numerical stability and unit discipline of translations.",
                formula=r"\text{HUF bp}\to\text{USD bp}\to\text{HUF bp}",
                methodology_rationale="Translate out and back; residual should be near zero.",
                inputs_used="Input HUF spread, computed USD translation, and reverse translation.",
                substituted_values=(
                    f"${round_trip['huf_bp_in']:.2f}\\to{round_trip['usd_bp_translated']:.2f}"
                    f"\\to{round_trip['huf_bp_round_trip']:.2f}$"
                ),
                derivation_steps=("Translate HUF to USD using CF.", "Translate USD back to HUF.", "Measure residual.",),
                assumptions=("Same CF convention used both directions.",),
                interpretation="Residual near zero validates conversion consistency.",
                common_misunderstandings=("Comparing translated values without checking round-trip error.",),
                result=(
                    f"residual={round_trip['round_trip_residual_bp']:.6f} bp"
                    f" | tol={round_trip['tolerance_bp']:.6f}"
                    f" | pass={round_trip['round_trip_within_tolerance']}"
                ),
            ),
            CalculationWindow(
                title="Pickup decomposition",
                concept_meaning="Net hedged pickup decomposition from gross carry to executable edge.",
                why_it_matters="Shows where nominal differential is consumed by costs.",
                formula=r"\text{Net}=\text{Gross}-\text{Hedge}-\text{Basis}-\text{Extra}",
                methodology_rationale="Subtract each implementation drag from gross pickup.",
                inputs_used="Gross pickup, hedge cost, basis drag, extra friction (bps).",
                substituted_values=(
                    f"${base['gross_pickup_bp']:.2f}-{base['hedge_cost_bp']:.2f}"
                    f"-{base['basis_drag_bp']:.2f}-{base['extra_friction_bp']:.2f}$"
                ),
                derivation_steps=("Start from gross pickup.", "Subtract hedge and basis drag.", "Subtract residual frictions.",),
                assumptions=("Cost terms are additive at the chosen horizon.",),
                interpretation="Positive result indicates remaining hedged carry after costs.",
                common_misunderstandings=("Equating nominal carry with realizable pickup.",),
                result=f"{base['net_hedged_pickup_bp']:.2f} bps",
            ),
            CalculationWindow(
                title="Matched vs rolling hedge",
                concept_meaning="Risk-adjusted comparison of hedge implementations.",
                why_it_matters="Determines preferred hedge structure beyond expected carry.",
                formula=r"\text{RA roll}=C_{roll}+\lambda\cdot \sigma_{roll}",
                methodology_rationale="Penalize rolling strategy by volatility-scaled risk term.",
                inputs_used="Matched cost, expected rolling cost, roll risk proxy, risk aversion.",
                substituted_values=(
                    f"$C_m={base['matched_cost_bp']:.2f}, C_r={base['expected_rolling_cost_bp']:.2f},"
                    f" \\sigma={base['roll_risk_proxy_bp']:.2f},"
                    f" \\lambda={base['risk_aversion_multiplier']:.2f}$"
                ),
                derivation_steps=("Compute RA rolling cost.", "Compare against matched cost.", "Select cheaper risk-adjusted route.",),
                assumptions=("Risk aversion multiplier is user-appropriate.",),
                interpretation="Lower risk-adjusted cost determines preferred hedge.",
                common_misunderstandings=("Choosing rolling solely on expected drift without risk penalty.",),
                result=(
                    f"drift={base['expected_roll_drift_bp']:.2f}"
                    f" | RA roll={base['risk_adjusted_rolling_cost_bp']:.2f}"
                    f" | preferred={base['preferred_hedge']}"
                ),
            ),
        ]
    )


render_page()
