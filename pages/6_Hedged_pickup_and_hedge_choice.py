from __future__ import annotations

from page_layout import render_lesson
from src.analytics.conversion_factor import conversion_factor_curve_aware, conversion_factor_simple


def _conversion_demo(frame):
    tenors_years = (frame["Tenor (M)"] / 12).tolist()
    basis_bps = frame["Basis (bps)"].tolist()

    spot = 360.0
    # Synthetic forwards: small carry term + tenor-varying basis effect.
    forwards = [spot * (1 + 0.01 * t) * (1 + b / 10_000) for t, b in zip(tenors_years, basis_bps)]
    discount_factors = [1 / (1 + 0.05 * t) for t in tenors_years]
    accruals = [
        tenors_years[0],
        *[tenors_years[i] - tenors_years[i - 1] for i in range(1, len(tenors_years))],
    ]

    simple_payload = conversion_factor_simple(spot_huf_per_usd=spot, forward_huf_per_usd=forwards[-1])
    curve_payload = conversion_factor_curve_aware(
        spot_huf_per_usd=spot,
        forward_huf_per_usd_by_tenor=forwards,
        tenor_years=tenors_years,
        discount_factors=discount_factors,
        accrual_factors=accruals,
    )
    return simple_payload, curve_payload


def explain(frame):
    pickup = frame.iloc[-1]["Carry differential (%)"] + frame.iloc[-1]["Basis (bps)"] / 100
    simple_payload, curve_payload = _conversion_demo(frame)
    simple_cf = simple_payload["conversion_factor"]
    curve_cf = curve_payload["conversion_factor"]
    divergence_bp_on_100 = (curve_cf - simple_cf) * 100

    return (
        f"Indicative long-tenor hedged pickup is {pickup:.2f}% after basis adjustment. "
        f"Simple FX ratio CF={simple_cf:.4f} (single-tenor forward) versus "
        f"curve-aware CF={curve_cf:.4f} (annuity-weighted across tenor buckets). "
        f"For a 100 bp source spread, the methods differ by {divergence_bp_on_100:.2f} bp. "
        "Divergence appears when forward points and discounting vary across the tenor structure."
    )


render_lesson(
    step_index=5,
    title="6. Hedged pickup and hedge choice",
    summary="Compare all-in pickup under forwards vs cross-currency swaps and relate it to hedge design choices.",
    metric_defs=[
        ("All-in pickup", "basis-adjusted", "instrument-sensitive"),
        ("Rollover risk", "path-dependent", "hedge-horizon linked"),
        ("Liquidity cost", "market-state linked", "execution-dependent"),
    ],
    explanation_fn=explain,
    theory_text=(
        "The best hedge is not always the highest-carry one; governance, liquidity, and accounting outcomes matter. "
        "A single forward/spot ratio is easy to communicate, while a curve-aware annuity weighting better represents "
        "multi-period swap cash-flow translation."
    ),
    calc_text=(
        "Both conversion-factor methods are displayed in the dynamic explanation: "
        "CF_simple = F_T / S_0 and CF_curve = Σ_i w_i(F_i/S_0), with w_i ∝ DF_i·Δ_i. "
        "They match only under flat forward ratios/weights; otherwise CF_curve captures term-structure effects "
        "and can materially shift translated bp pickup."
    ),
)
