import math

import pytest

from tests._test_utils import CANDIDATE_MODULES, try_import_any


def _arbitrage_band(mid: float, half_width: float) -> tuple[float, float]:
    if half_width < 0:
        raise ValueError("half_width cannot be negative")
    return mid - half_width, mid + half_width


def test_arbitrage_band_symmetry():
    assert _arbitrage_band(12.0, 3.0) == (9.0, 15.0)


@pytest.mark.parametrize("mid,half_width", [(0.0, 0.0), (1e8, 1e6), (-1e8, 1e6)])
def test_arbitrage_band_extremes(mid, half_width):
    lo, hi = _arbitrage_band(mid, half_width)
    assert math.isfinite(lo)
    assert math.isfinite(hi)
    assert lo <= hi


def test_arbitrage_band_guardrail_rejects_negative_half_width():
    with pytest.raises(ValueError):
        _arbitrage_band(mid=0.0, half_width=-0.1)


def test_project_arbitrage_band_module_exposes_callables_when_present():
    mod = try_import_any(CANDIDATE_MODULES["arbitrage_band"])
    if mod is None:
        pytest.skip("No arbitrage_band module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
