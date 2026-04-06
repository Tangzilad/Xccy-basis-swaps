import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("pandas")

from src.synthetic import market_generator as mg  # noqa: E402


def test_cip_consistent_baseline_forward_shape():
    state = mg.generate_market(seed=1, regime="baseline")
    usd_df = state["usd_curve_df"]["discount_factor"].to_numpy()
    huf_df = state["huf_curve_df"]["discount_factor"].to_numpy()

    implied_theoretical = state["spot_fx"] * usd_df / np.maximum(huf_df, 1e-12)
    published_theoretical = state["theoretical_forward_df"]["theoretical_forward"].to_numpy()
    assert np.allclose(implied_theoretical, published_theoretical, atol=1e-10)


def test_generator_clipping_and_repair_guardrails():
    t = np.array([0.25, 0.5, 1.0, 2.0, 3.0])
    pathological_df = np.array([1.2, 1.1, 0.9, 0.95, -0.4])

    repaired = mg._repair_discount_curve(pathological_df, t)

    assert np.all(np.isfinite(repaired))
    assert np.all(repaired <= 1.0)
    assert np.all(repaired >= 1e-6)
    assert np.all(np.diff(repaired) <= 0.0)


def test_generator_is_deterministic_for_fixed_seed():
    a = mg.generate_market(seed=42, regime="stress")
    b = mg.generate_market(seed=42, regime="stress")

    for key in ("market_forward_df", "theoretical_forward_df", "basis_curve_df", "credit_assumptions", "friction_assumptions"):
        assert a[key].equals(b[key]), f"non-deterministic output for {key}"
