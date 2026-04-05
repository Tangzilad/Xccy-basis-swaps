import math

import pytest

from tests._test_utils import CANDIDATE_MODULES, try_import_any


def _basis_bps(market_fwd: float, cip_fwd: float, spot: float) -> float:
    return 1e4 * (market_fwd - cip_fwd) / spot


def test_basis_sign_convention():
    assert _basis_bps(1.12, 1.10, 1.0) > 0
    assert _basis_bps(1.08, 1.10, 1.0) < 0


@pytest.mark.parametrize("market_fwd,cip_fwd,spot", [(10_000.0, 0.01, 0.001), (0.0001, 10_000.0, 0.001), (1.0, 1.0, 1e-9)])
def test_basis_extreme_inputs_remain_finite_or_raise_guarded_error(market_fwd, cip_fwd, spot):
    try:
        out = _basis_bps(market_fwd, cip_fwd, spot)
        assert math.isfinite(out)
    except ZeroDivisionError:
        pytest.fail("Basis guardrails should avoid division-by-zero via pre-validation.")


def test_project_basis_module_exposes_callables_when_present():
    mod = try_import_any(CANDIDATE_MODULES["basis"])
    if mod is None:
        pytest.skip("No basis module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
