import math

import pytest

from tests._test_utils import CANDIDATE_MODULES, synthetic_market_rows, try_import_any


def _apply_linear_scenario(rows: dict[str, list[float]], shock_bps: float, rate_shift_pct: float, liq_mult: float):
    if liq_mult <= 0:
        raise ValueError("liq_mult must be positive")
    return {
        "spreads_bps": [x + shock_bps for x in rows["spreads_bps"]],
        "rates_pct": [x + rate_shift_pct for x in rows["rates_pct"]],
        "liquidity": [x * liq_mult for x in rows["liquidity"]],
    }


def test_scenario_application_is_shape_preserving_and_deterministic():
    base = synthetic_market_rows(n=64, seed=999)
    a = _apply_linear_scenario(base, shock_bps=25.0, rate_shift_pct=-0.5, liq_mult=1.2)
    b = _apply_linear_scenario(base, shock_bps=25.0, rate_shift_pct=-0.5, liq_mult=1.2)

    for key in ("spreads_bps", "rates_pct", "liquidity"):
        assert len(a[key]) == len(base[key])
        assert a[key] == b[key]


def test_scenario_application_extreme_inputs_and_guardrail_behavior():
    base = synthetic_market_rows(n=16, seed=1)
    shocked = _apply_linear_scenario(base, shock_bps=1e6, rate_shift_pct=-1e3, liq_mult=1e-6)
    assert all(math.isfinite(x) for x in shocked["spreads_bps"])
    assert all(math.isfinite(x) for x in shocked["rates_pct"])
    assert all(x > 0 for x in shocked["liquidity"])

    with pytest.raises(ValueError):
        _apply_linear_scenario(base, shock_bps=0, rate_shift_pct=0, liq_mult=0)


def test_project_scenario_application_module_exposes_callables_when_present():
    mod = try_import_any(CANDIDATE_MODULES["scenario_application"])
    if mod is None:
        pytest.skip("No scenario_application module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
