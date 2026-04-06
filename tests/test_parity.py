import math

import pytest

from src.analytics.parity import (
    cip_theoretical_forward,
    fair_value_comparison,
    implied_huf_rate_from_spot_forward,
)
from tests._test_utils import CANDIDATE_MODULES, try_import_any


def _covered_interest_parity_spread(spot: float, fwd: float, r_dom: float, r_for: float, t: float) -> float:
    lhs = fwd / spot
    rhs = (1.0 + r_dom * t) / (1.0 + r_for * t)
    return lhs - rhs


def test_parity_identity_zero_spread_when_inputs_match():
    spot = 1.1
    r_dom, r_for, t = 0.04, 0.02, 1.0
    fwd = spot * ((1 + r_dom * t) / (1 + r_for * t))
    spread = _covered_interest_parity_spread(spot, fwd, r_dom, r_for, t)
    assert math.isclose(spread, 0.0, abs_tol=1e-12)


def test_cip_identity_consistency_with_implied_huf_recovery() -> None:
    spot = 372.0
    usd_rate = 0.052
    huf_rate = 0.074
    year_fraction = 1.25

    forward = cip_theoretical_forward(spot, usd_rate, huf_rate, year_fraction)
    recovered = implied_huf_rate_from_spot_forward(spot, forward, usd_rate, year_fraction)

    assert math.isclose(recovered, huf_rate, rel_tol=0.0, abs_tol=1e-12)


@pytest.mark.parametrize("spot,fwd,r_dom,r_for,t", [(1.0, 1.0, 0.0, 0.0, 1.0), (0.85, 0.92, 0.08, -0.01, 0.25), (150.0, 148.0, 0.015, 0.012, 2.0)])
def test_parity_formula_returns_finite_values_for_extremes(spot, fwd, r_dom, r_for, t):
    spread = _covered_interest_parity_spread(spot, fwd, r_dom, r_for, t)
    assert math.isfinite(spread)


@pytest.mark.parametrize("deviation", [8.5, -8.5])
def test_raw_basis_wedge_sign_logic_tracks_forward_deviation(deviation: float) -> None:
    spot = 365.0
    usd_rate = 0.048
    huf_rate = 0.067
    year_fraction = 1.0

    fair = cip_theoretical_forward(spot, usd_rate, huf_rate, year_fraction)
    observed = fair + deviation

    out = fair_value_comparison(
        spot_huf_per_usd=spot,
        observed_forward_huf_per_usd=observed,
        usd_rate=usd_rate,
        huf_rate=huf_rate,
        year_fraction=year_fraction,
    )

    assert math.copysign(1.0, out["forward_difference"]) == math.copysign(1.0, deviation)
    assert math.copysign(1.0, out["raw_basis_wedge_bp"]) == math.copysign(1.0, deviation)


def test_project_parity_module_exposes_at_least_one_callable_when_present():
    mod = try_import_any(CANDIDATE_MODULES["parity"])
    if mod is None:
        pytest.skip("No parity module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
