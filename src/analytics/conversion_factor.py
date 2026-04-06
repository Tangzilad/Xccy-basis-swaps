"""Conversion-factor and spread translation utilities.

Canonical sign convention
-------------------------
- Spreads are signed in basis points (bp).
- Positive spread means the first market named in the statement is *wider*.
- Conversion factors are positive multipliers that map one quote convention into another.

Direction examples
------------------
Let CF be the conversion factor from HUF-bp to USD-bp:

- HUF → USD translation: ``usd_bp = huf_bp * CF``
- USD → HUF translation: ``huf_bp = usd_bp / CF``

If a +20 bp HUF spread and ``CF = 0.92``:
- HUF → USD gives +18.4 bp.
- USD → HUF for +18.4 bp gives +20 bp back.
"""

from __future__ import annotations

from typing import Any


def _validate_positive_finite(name: str, value: float) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")


def _validate_vector(name: str, values: list[float], *, strictly_positive: bool = True) -> None:
    if not values:
        raise ValueError(f"{name} cannot be empty")
    for idx, val in enumerate(values):
        if not isinstance(val, (int, float)):
            raise TypeError(f"{name}[{idx}] must be a real number")
        if val != val or val in (float("inf"), float("-inf")):
            raise ValueError(f"{name}[{idx}] must be finite")
        if strictly_positive and val <= 0:
            raise ValueError(f"{name}[{idx}] must be positive")


def _extract_conversion_factor(value: float | dict[str, Any]) -> float:
    if isinstance(value, dict):
        factor = value.get("conversion_factor")
        if not isinstance(factor, (int, float)):
            raise TypeError("conversion payload must include numeric 'conversion_factor'")
        return float(factor)
    if not isinstance(value, (int, float)):
        raise TypeError("conversion_factor must be numeric or a conversion payload")
    return float(value)


def conversion_factor_simple(spot_huf_per_usd: float, forward_huf_per_usd: float) -> dict[str, Any]:
    """Compute a simple forward/spot conversion factor.

    Formula
    -------
    ``CF_simple = F / S`` where:
    - ``S`` = spot FX in HUF per USD
    - ``F`` = forward FX for matching tenor in HUF per USD

    Returns a structured payload for UI calculation panels.
    """
    _validate_positive_finite("spot_huf_per_usd", spot_huf_per_usd)
    _validate_positive_finite("forward_huf_per_usd", forward_huf_per_usd)

    factor = forward_huf_per_usd / spot_huf_per_usd
    return {
        "method": "simple_ratio",
        "conversion_factor": factor,
        "inputs": {
            "spot_huf_per_usd": float(spot_huf_per_usd),
            "forward_huf_per_usd": float(forward_huf_per_usd),
        },
        "components": {
            "ratio_numerator": float(forward_huf_per_usd),
            "ratio_denominator": float(spot_huf_per_usd),
        },
    }


def conversion_factor_curve_aware(
    *,
    spot_huf_per_usd: float,
    forward_huf_per_usd_by_tenor: list[float],
    tenor_years: list[float],
    discount_factors: list[float],
    accrual_factors: list[float] | None = None,
) -> dict[str, Any]:
    """Compute a curve-aware conversion factor using annuity-style tenor weights.

    Formula
    -------
    For tenor buckets ``i = 1..N``:

    - Bucket ratio: ``r_i = F_i / S``
    - Bucket weight before normalization: ``a_i = DF_i * Δ_i``
    - Normalized annuity weight: ``w_i = a_i / Σ_j a_j``
    - Curve-aware conversion factor: ``CF_curve = Σ_i w_i * r_i``

    Required inputs
    ---------------
    - ``spot_huf_per_usd``: spot FX level ``S`` (HUF per USD), strictly positive.
    - ``forward_huf_per_usd_by_tenor``: tenor-specific forwards ``F_i``, strictly positive.
    - ``tenor_years``: tenor labels in years (for diagnostics/display), finite positive values.
    - ``discount_factors``: curve discount factors ``DF_i`` used for annuity weighting, finite positive values.
    - ``accrual_factors`` (optional): ``Δ_i`` per bucket. If omitted, defaults to 1.0 for every bucket.

    Sign convention examples
    ------------------------
    - HUF → USD: ``usd_bp = huf_bp * CF_curve``
    - USD → HUF: ``huf_bp = usd_bp / CF_curve``
    """
    _validate_positive_finite("spot_huf_per_usd", spot_huf_per_usd)
    _validate_vector("forward_huf_per_usd_by_tenor", forward_huf_per_usd_by_tenor)
    _validate_vector("tenor_years", tenor_years)
    _validate_vector("discount_factors", discount_factors)

    n = len(forward_huf_per_usd_by_tenor)
    if len(tenor_years) != n or len(discount_factors) != n:
        raise ValueError(
            "forward_huf_per_usd_by_tenor, tenor_years, and discount_factors must have the same length"
        )

    if accrual_factors is None:
        accrual_factors = [1.0] * n
    _validate_vector("accrual_factors", accrual_factors)
    if len(accrual_factors) != n:
        raise ValueError("accrual_factors must match tenor vector length")

    annuity_terms = [df * acc for df, acc in zip(discount_factors, accrual_factors)]
    annuity_sum = sum(annuity_terms)
    _validate_positive_finite("annuity_sum", annuity_sum)

    weights = [term / annuity_sum for term in annuity_terms]
    bucket_ratios = [fwd / spot_huf_per_usd for fwd in forward_huf_per_usd_by_tenor]
    weighted_ratios = [w * r for w, r in zip(weights, bucket_ratios)]
    factor = sum(weighted_ratios)

    return {
        "method": "curve_aware_annuity",
        "conversion_factor": factor,
        "inputs": {
            "spot_huf_per_usd": float(spot_huf_per_usd),
            "forward_huf_per_usd_by_tenor": [float(x) for x in forward_huf_per_usd_by_tenor],
            "tenor_years": [float(x) for x in tenor_years],
            "discount_factors": [float(x) for x in discount_factors],
            "accrual_factors": [float(x) for x in accrual_factors],
        },
        "components": {
            "annuity_terms": [float(x) for x in annuity_terms],
            "annuity_sum": float(annuity_sum),
            "weights": [float(x) for x in weights],
            "bucket_ratios": [float(x) for x in bucket_ratios],
            "weighted_bucket_ratios": [float(x) for x in weighted_ratios],
        },
    }


def conversion_factor_from_fx(spot_huf_per_usd: float, forward_huf_per_usd: float) -> float:
    """Backward-compatible alias for the simple ratio conversion factor."""
    return conversion_factor_simple(spot_huf_per_usd, forward_huf_per_usd)["conversion_factor"]


def translate_spread_bp(spread_bp: float, conversion_factor: float | dict[str, Any]) -> float:
    """Translate a spread using either a raw factor or a conversion payload."""
    return spread_bp * _extract_conversion_factor(conversion_factor)


def translate_spread_inverse_bp(
    translated_spread_bp: float, conversion_factor: float | dict[str, Any]
) -> float:
    """Invert spread translation using either a raw factor or a conversion payload."""
    return translated_spread_bp / _extract_conversion_factor(conversion_factor)


def spread_translation_round_trip_bp(
    huf_spread_bp: float,
    conversion_factor: float | dict[str, Any],
    *,
    tolerance_bp: float = 1e-9,
) -> dict[str, float | bool]:
    """Run HUF-bp -> USD-bp -> HUF-bp round-trip and validate tolerance."""
    if tolerance_bp < 0:
        raise ValueError("tolerance_bp must be non-negative")
    usd_spread_bp = translate_spread_bp(huf_spread_bp, conversion_factor)
    recovered_huf_spread_bp = translate_spread_inverse_bp(usd_spread_bp, conversion_factor)
    residual_bp = recovered_huf_spread_bp - huf_spread_bp
    return {
        "huf_bp_in": huf_spread_bp,
        "usd_bp_translated": usd_spread_bp,
        "huf_bp_round_trip": recovered_huf_spread_bp,
        "round_trip_residual_bp": residual_bp,
        "round_trip_within_tolerance": abs(residual_bp) <= tolerance_bp,
        "tolerance_bp": tolerance_bp,
    }
