import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")


import copy
import json

from src.scenarios.scenario_library import apply_scenario, capital_outflow_shock
from src.synthetic.market_generator import generate_market


def test_market_state_initialization_via_generator_is_deterministic():
    a = generate_market(seed=2026, regime="baseline")
    b = generate_market(seed=2026, regime="baseline")

    required = {
        "tenors",
        "huf_curve_df",
        "usd_curve_df",
        "spot_fx",
        "market_forward_df",
        "theoretical_forward_df",
        "basis_curve_df",
        "credit_assumptions",
        "friction_assumptions",
        "regime_summary",
    }
    assert set(a) == required
    assert a["tenors"] == b["tenors"]
    assert a["spot_fx"] == b["spot_fx"]
    assert a["regime_summary"] == b["regime_summary"]
    assert a["market_forward_df"].equals(b["market_forward_df"])


def test_market_state_control_patching_changes_regime_as_expected():
    baseline = generate_market(seed=7, regime="baseline")
    patched = generate_market(seed=7, regime={"name": "patched", "level": 0.8, "slope": 0.25, "curvature": 0.2, "noise_scale": 1.0})

    assert patched["regime_summary"]["name"] == "patched"
    assert patched["regime_summary"]["stress_score"] > baseline["regime_summary"]["stress_score"]
    assert not patched["market_forward_df"].equals(baseline["market_forward_df"])


def test_market_state_scenario_application_and_persistence_round_trip(base_snapshot: dict):
    scenario = capital_outflow_shock()
    pre = copy.deepcopy(base_snapshot)

    shocked_a = apply_scenario(scenario, base_snapshot)
    shocked_b = scenario.apply(base_snapshot)

    assert shocked_a == shocked_b
    assert base_snapshot == pre, "scenario application should not mutate original state"

    payload = {"base": base_snapshot, "stressed": shocked_a}
    restored = json.loads(json.dumps(payload))
    assert restored["base"]["spot"] == base_snapshot["spot"]
    assert restored["stressed"]["spot"] == shocked_a["spot"]
    assert restored["stressed"]["huf_rates"]["front"] > restored["base"]["huf_rates"]["front"]
