from __future__ import annotations

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_state_scenario,
    ensure_market_state,
    regenerate_market_state,
)


def test_regenerate_market_state_resets_stress_snapshot() -> None:
    state = ensure_market_state(None, seed=12)
    state = regenerate_market_state(state)

    assert state["scenario"] == "none"
    assert state["base_snapshot"]["basis_curve_df"].equals(state["stressed_snapshot"]["basis_curve_df"])


def test_apply_state_scenario_preserves_base_and_updates_stress() -> None:
    state = ensure_market_state(None, seed=3)
    base_before = state["base_snapshot"]["basis_curve_df"].copy()

    shocked = apply_state_scenario(state, SCENARIO_LIBRARY["usd_funding_shortage"])

    assert shocked["scenario"] == "usd_funding_shortage"
    assert shocked["base_snapshot"]["basis_curve_df"].equals(base_before)
    assert not shocked["stressed_snapshot"]["basis_curve_df"].equals(base_before)
