from __future__ import annotations

import streamlit as st

from shared_page_helpers import get_market_params, render_page_footer, render_page_header
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
from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


def render_page() -> None:
    st.set_page_config(page_title="6. Hedged pickup and hedge choice", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[5]

    # --- Market context ---
    summary = get_canonical_market_context(st.session_state)["summary_1y"]["base"]
    m = get_market_params(st.session_state)
    spot = float(m["spot_fx"])
    usd = float(m["usd_rate"])
    huf = float(m["huf_rate"])
    basis = float(m["basis_bps"])

    fwd = spot * (1 + huf) / (1 + usd)

    # --- Conversion factors ---
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

    # --- Pickup calculations ---
    nominal_diff_bp = (huf - usd) * 10_000
    gross = translate_spread_bp(nominal_diff_bp, curve_cf)
    round_trip = spread_translation_round_trip_bp(nominal_diff_bp, curve_cf, tolerance_bp=1e-6)

    rows = []
    for hc in [20.0, 35.0, 50.0]:
        rp = roll_cost_and_risk_proxy_bp(hc, hc + 5.0, 18.0, 1.0)
        ch = matched_vs_rolling_hedge_economics_bp(hc + 12.0, hc, rp["roll_risk_proxy_bp"], 0.6)
        decomp = hedged_pickup_decomposition_bp(gross, hc, abs(basis), 8.0)
        rows.append({"hedge_cost": hc, "pickup": decomp["net_hedged_pickup_bp"], **decomp, **rp, **ch})
    base = next(r for r in rows if r["hedge_cost"] == 35.0)

    # --- Header with learning objectives ---
    render_page_header(5, "6. Hedged Pickup and Hedge Choice")

    # --- Metrics ---
    a, b, c, d = st.columns(4)
    a.metric("Simple CF (F/S)", f"{simple_cf:.6f}")
    b.metric("Curve-aware CF", f"{curve_cf:.6f}")
    c.metric("Converted gross", f"{gross:.2f} bps")
    d.metric("Net pickup", f"{base['pickup']:.2f} bps")
    st.caption(f"Preferred hedge method (base case): **{str(base['preferred_hedge']).title()}**")

    # --- Charts ---
    st.line_chart(
        {
            "hedge_cost": [r["hedge_cost"] for r in rows],
            "pickup": [r["pickup"] for r in rows],
            "benefit_of_rolling": [r["benefit_of_rolling_bp"] for r in rows],
        },
        x="hedge_cost",
    )
    st.dataframe(rows, use_container_width=True)

    # --- Explanatory content ---
    st.markdown(
        """
**Why CF is not "just FX":** the conversion factor is the map from one quote space (HUF-bp) into another
(USD-bp). Spot alone does not control that map -- forward points and curve weights matter, which is why the
curve-aware CF can differ from the simple (F/S) ratio.

**Why hedged pickup differs from nominal yield differential:** the nominal HUF-USD differential is only a
starting point. Realized hedged pickup subtracts hedge implementation cost, basis drag, and frictions.
Therefore "higher nominal yield" can still produce weak or negative net pickup after hedging.
"""
    )

    learning_hint(
        "Compare the curve-aware CF against the simple CF. When do they diverge materially? "
        "This matters because the wrong conversion factor can make you think a trade is profitable "
        "when it is not. Rolling hedges introduce mark-to-market risk scaled by volatility."
    )

    # --- Calculation windows ---
    render_calculation_windows(
        [
            CalculationWindow(
                "Simple conversion factor",
                r"CF_{simple}=F/S",
                f"$F={fwd:.4f}, S={spot:.4f}$",
                ("Simple tenor-matched ratio for quote translation.",),
                result=f"{simple_cf:.6f}",
            ),
            CalculationWindow(
                "Curve-aware conversion factor",
                r"CF_{curve}=\sum_i w_i(F_i/S)",
                f"$\\sum_i w_i=1, S={spot:.4f}$",
                ("Weights use discount-factor annuity terms across tenor buckets.",),
                result=f"{curve_cf:.6f}",
            ),
            CalculationWindow(
                "Translated gross pickup",
                r"\text{gross}_{tr}=\text{nominal diff}\times CF",
                f"$\\text{{nominal diff}}={nominal_diff_bp:.2f}, CF={curve_cf:.6f}$",
                ("Positive is favorable before costs.",),
                result=f"{gross:.2f} bps",
            ),
            CalculationWindow(
                "Spread translation round-trip",
                r"\text{HUF bp}\to\text{USD bp}\to\text{HUF bp}",
                f"${round_trip['huf_bp_in']:.2f}\\to{round_trip['usd_bp_translated']:.2f}\\to{round_trip['huf_bp_round_trip']:.2f}$",
                ("Residual near zero validates conversion consistency.",),
                result=f"residual={round_trip['round_trip_residual_bp']:.6f} bp | pass={round_trip['round_trip_within_tolerance']}",
            ),
            CalculationWindow(
                "Pickup decomposition",
                r"\text{Net}=\text{Gross}-\text{Hedge}-\text{Basis drag}-\text{Extra friction}",
                f"${base['gross_pickup_bp']:.2f}-{base['hedge_cost_bp']:.2f}-{base['basis_drag_bp']:.2f}-{base['extra_friction_bp']:.2f}$",
                ("Gross pickup is reduced by implementable hedge and friction terms.",),
                result=f"{base['net_hedged_pickup_bp']:.2f} bps",
            ),
            CalculationWindow(
                "Matched vs rolling hedge",
                r"\text{RA roll}=C_{roll}+\lambda\cdot \sigma_{roll}",
                f"$C_m={base['matched_cost_bp']:.2f}, C_r={base['expected_rolling_cost_bp']:.2f}, "
                f"\\sigma={base['roll_risk_proxy_bp']:.2f}, \\lambda={base['risk_aversion_multiplier']:.2f}$",
                ("Compare matched cost against risk-adjusted rolling cost.",),
                result=f"drift={base['expected_roll_drift_bp']:.2f} | RA roll={base['risk_adjusted_rolling_cost_bp']:.2f} | preferred={base['preferred_hedge']}",
            ),
        ]
    )

    # --- Pedagogical footer ---
    render_page_footer(5)


if __name__ == "__main__":
    render_page()
else:
    render_page()
