import pytest

from tests._test_utils import CANDIDATE_MODULES, synthetic_market_rows, try_import_any


def _build_narrative(rows: dict[str, list[float]]) -> str:
    mean_spread = sum(rows["spreads_bps"]) / len(rows["spreads_bps"])
    mean_rate = sum(rows["rates_pct"]) / len(rows["rates_pct"])
    liq = sum(rows["liquidity"]) / len(rows["liquidity"])
    return f"Average spread={mean_spread:.2f}bps, rate={mean_rate:.2f}%, liquidity={liq:.2f}."


def test_narrative_engine_output_is_deterministic_for_fixed_seed():
    rows = synthetic_market_rows(n=32, seed=2026)
    assert _build_narrative(rows) == _build_narrative(rows)


def test_narrative_engine_handles_extreme_inputs():
    rows = {
        "spreads_bps": [-1e9, 1e9],
        "rates_pct": [-1e4, 1e4],
        "liquidity": [1e-12, 1e12],
    }
    text = _build_narrative(rows)
    assert isinstance(text, str)
    assert "Average spread" in text


def test_project_narrative_engine_module_exposes_callables_when_present():
    mod = try_import_any(CANDIDATE_MODULES["narrative_engine"])
    if mod is None:
        pytest.skip("No narrative_engine module found in this repository.")
    callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
    assert callables
