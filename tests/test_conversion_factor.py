import math

import pytest

from tests._test_utils import CANDIDATE_MODULES, try_import_any


def _conversion_factor(day_count_fraction: float, notional: float = 1.0) -> float:
    if day_count_fraction < 0:
        raise ValueError("day_count_fraction must be non-negative")
    return notional * day_count_fraction


def test_conversion_factor_monotonicity():
    xs = [0.0, 0.25, 0.5, 1.0]
    ys = [_conversion_factor(x) for x in xs]
    assert ys == sorted(ys)


def test_conversion_factor_guardrail_on_negative_input():
    with pytest.raises(ValueError):
        _conversion_factor(-1e-9)


@pytest.mark.parametrize("x", [0.0, 1e-12, 1e6])
def test_conversion_factor_finite(x):
    val = _conversion_factor(x, notional=1e9)
    assert math.isfinite(val)


def test_project_conversion_factor_module_exposes_callables_when_present():
    mod = try_import_any(CANDIDATE_MODULES["conversion_factor"])
    if mod is None:
        pytest.skip("No conversion_factor module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
