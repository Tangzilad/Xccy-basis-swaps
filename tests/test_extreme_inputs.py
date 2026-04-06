import math

import pytest

from tests._test_utils import synthetic_market_rows


def _guardrails(spreads_bps: list[float], rates_pct: list[float], liquidity: list[float]) -> tuple[list[float], list[float], list[float]]:
    clipped_spreads = [max(-1e6, min(1e6, x)) for x in spreads_bps]
    clipped_rates = [max(-1e3, min(1e3, x)) for x in rates_pct]
    floored_liquidity = [max(1e-12, x) for x in liquidity]
    return clipped_spreads, clipped_rates, floored_liquidity


def test_guardrails_clip_extreme_values_and_preserve_finite_outputs():
    spreads = [-1e9, 0.0, 1e9]
    rates = [-1e6, 0.0, 1e6]
    liquidity = [-1e9, 0.0, 1e9]

    s, r, liq_values = _guardrails(spreads, rates, liquidity)
    assert all(math.isfinite(x) for x in s)
    assert all(math.isfinite(x) for x in r)
    assert all(x > 0 for x in liq_values)
    assert s[0] == -1e6 and s[2] == 1e6
    assert r[0] == -1e3 and r[2] == 1e3


def test_guardrails_are_deterministic_under_seeded_synthetic_data():
    data = synthetic_market_rows(n=128, seed=1234)
    out1 = _guardrails(data["spreads_bps"], data["rates_pct"], data["liquidity"])
    out2 = _guardrails(data["spreads_bps"], data["rates_pct"], data["liquidity"])
    assert out1 == out2


@pytest.mark.parametrize("spreads,rates,liq", [([0.0], [0.0], [1.0]), ([1e12], [-1e12], [1e-30])])
def test_guardrails_handle_small_and_huge_inputs(spreads, rates, liq):
    s, r, liq_values = _guardrails(spreads, rates, liq)
    assert all(math.isfinite(x) for x in s)
    assert all(math.isfinite(x) for x in r)
    assert all(x >= 1e-12 for x in liq_values)
