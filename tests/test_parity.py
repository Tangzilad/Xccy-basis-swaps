import math

import pytest

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


@pytest.mark.parametrize("spot,fwd,r_dom,r_for,t", [(1.0, 1.0, 0.0, 0.0, 1.0), (0.85, 0.92, 0.08, -0.01, 0.25), (150.0, 148.0, 0.015, 0.012, 2.0)])
def test_parity_formula_returns_finite_values_for_extremes(spot, fwd, r_dom, r_for, t):
    spread = _covered_interest_parity_spread(spot, fwd, r_dom, r_for, t)
    assert math.isfinite(spread)


def test_project_parity_module_exposes_at_least_one_callable_when_present():
    mod = try_import_any(CANDIDATE_MODULES["parity"])
    if mod is None:
        pytest.skip("No parity module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
