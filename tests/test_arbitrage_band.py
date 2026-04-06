import math

import pytest

from src.analytics.frictions import deposit_adjusted_arbitrage_band_bp
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


def test_deposit_adjusted_actionability_transition_with_overlay_increase() -> None:
    baseline = deposit_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=40.0,
        base_friction_bp=18.0,
        deposit_borrowing_bp=5.0,
        cva_bp=3.0,
        fva_bp=2.0,
        capital_charge_bp=1.0,
    )
    stressed = deposit_adjusted_arbitrage_band_bp(
        raw_basis_edge_bp=40.0,
        base_friction_bp=18.0,
        deposit_borrowing_bp=11.0,
        cva_bp=5.0,
        fva_bp=4.0,
        capital_charge_bp=3.0,
    )

    assert baseline["is_actionable"] is True
    assert baseline["net_edge_bp"] == pytest.approx(11.0)

    assert stressed["is_actionable"] is False
    assert stressed["net_edge_bp"] == pytest.approx(-1.0)
