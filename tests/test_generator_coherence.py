from tests._test_utils import synthetic_market_rows


def test_synthetic_generator_is_deterministic_for_fixed_seed():
    a = synthetic_market_rows(n=100, seed=42)
    b = synthetic_market_rows(n=100, seed=42)

    assert set(a) == {"spreads_bps", "rates_pct", "liquidity"}
    for key in a:
        assert a[key] == b[key], f"non-deterministic output for {key}"


def test_synthetic_generator_shapes_and_basic_ranges():
    rows = synthetic_market_rows(n=128, seed=7)

    assert len(rows["spreads_bps"]) == 128
    assert len(rows["rates_pct"]) == 128
    assert len(rows["liquidity"]) == 128
    assert all(x > 0.0 for x in rows["liquidity"])
