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


def _get_market_state(session_state: dict) -> object:
    return session_state.get("market_state")


def _build_payload(session_state: dict) -> dict[str, object]:
    context = get_canonical_market_context(session_state)
    base_summary = context["summary_1y"]["base"]

    spot = float(base_summary["spot_fx"])
    usd = float(base_summary["usd_rate"])
    huf = float(base_summary["huf_rate"])
    basis = float(base_summary["basis_bps"])
    fwd_1y = spot * (1 + huf) / (1 + usd)

    simple_cf_payload = conversion_factor_simple(spot, fwd_1y)
    simple_cf = float(simple_cf_payload["conversion_factor"])

    tenor_years = [0.5, 1.0, 2.0]
    forward_curve = [spot * (1 + huf * tenor) / (1 + usd * tenor) for tenor in tenor_years]
    discount_factors = [1.0 / (1.0 + usd * tenor) for tenor in tenor_years]
    curve_cf_payload = conversion_factor_curve_aware(
        spot_huf_per_usd=spot,
        forward_huf_per_usd_by_tenor=forward_curve,
        tenor_years=tenor_years,
        discount_factors=discount_factors,
    )
    curve_cf = float(curve_cf_payload["conversion_factor"])

    nominal_diff_bp = (huf - usd) * 10_000.0
    gross_pickup_bp = translate_spread_bp(nominal_diff_bp, curve_cf)
    round_trip = spread_translation_round_trip_bp(nominal_diff_bp, curve_cf, tolerance_bp=1e-6)

    rows: list[dict[str, float | str]] = []
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

    payload = _build_payload(st.session_state)

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
                "Simple conversion factor",
                r"CF_{simple}=F/S",
                f"$F={payload['fwd_1y']:.4f}, S={payload['spot']:.4f}$",
                ("Simple tenor-matched ratio for quote translation.",),
                result=f"{payload['simple_cf']:.6f}",
            ),
            CalculationWindow(
                "Curve-aware conversion factor",
                r"CF_{curve}=\sum_i w_i(F_i/S)",
                f"$\\sum_i w_i=1, S={payload['spot']:.4f}$",
                ("Weights use discount-factor annuity terms across tenor buckets.",),
                result=f"{payload['curve_cf']:.6f}",
            ),
            CalculationWindow(
                "Spread translation round-trip",
                r"\text{HUF bp}\to\text{USD bp}\to\text{HUF bp}",
                (
                    f"${round_trip['huf_bp_in']:.2f}\\to{round_trip['usd_bp_translated']:.2f}"
                    f"\\to{round_trip['huf_bp_round_trip']:.2f}$"
                ),
                ("Residual near zero validates conversion consistency.",),
                result=(
                    f"residual={round_trip['round_trip_residual_bp']:.6f} bp"
                    f" | tol={round_trip['tolerance_bp']:.6f}"
                    f" | pass={round_trip['round_trip_within_tolerance']}"
                ),
            ),
            CalculationWindow(
                "Pickup decomposition",
                r"\text{Net}=\text{Gross}-\text{Hedge}-\text{Basis}-\text{Extra}",
                (
                    f"${base['gross_pickup_bp']:.2f}-{base['hedge_cost_bp']:.2f}"
                    f"-{base['basis_drag_bp']:.2f}-{base['extra_friction_bp']:.2f}$"
                ),
                ("Gross pickup is reduced by implementable hedge and friction terms.",),
                result=f"{base['net_hedged_pickup_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Matched vs rolling hedge",
                r"\text{RA roll}=C_{roll}+\lambda\cdot \sigma_{roll}",
                (
                    f"$C_m={base['matched_cost_bp']:.2f}, C_r={base['expected_rolling_cost_bp']:.2f},"
                    f" \\sigma={base['roll_risk_proxy_bp']:.2f},"
                    f" \\lambda={base['risk_aversion_multiplier']:.2f}$"
                ),
                ("Compare matched cost against risk-adjusted rolling cost.",),
                result=(
                    f"drift={base['expected_roll_drift_bp']:.2f}"
                    f" | RA roll={base['risk_adjusted_rolling_cost_bp']:.2f}"
                    f" | preferred={base['preferred_hedge']}"
                ),
            ),
        ]
    )


if __name__ == "__main__":
    render_page()
