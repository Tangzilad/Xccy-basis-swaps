from __future__ import annotations


import pytest

from shared_page_helpers import get_market_params
from src.state.session_access import normalize_session_market_state
from src.state.market_state import apply_control_patch, init_market_state_from_generator, snapshot_for_narrative


def test_shared_helper_does_not_replace_canonical_market_state_with_shallow_dict() -> None:
    canonical = init_market_state_from_generator(seed=17, spot_fx=355.0, vol_regime="Normal", user_role="Learning")
    session_state = {
        "market_state": canonical,
        "selected_scenario": "stress",
        "suggested_page": "3. Parity lab",
        "custom_scenario_magnitude": 0.35,
        "base_rate": 4.25,
        "quote_rate": 5.00,
        "spot_fx": 355.0,
        "cross_currency_basis_bps": -28,
    }

    _ = get_market_params(session_state)
    assert session_state["market_state"] is canonical, "get_market_params should preserve canonical state"


def test_sidebar_control_patch_mutates_canonical_snapshots_deterministically() -> None:
    state_a = init_market_state_from_generator(seed=91, spot_fx=365.0, vol_regime="Normal", user_role="Learning")
    state_b = init_market_state_from_generator(seed=91, spot_fx=365.0, vol_regime="Normal", user_role="Learning")

    patch = {
        "mode": "Basic",
        "base_rate": 5.2,
        "quote_rate": 7.1,
        "spot_fx": 381.25,
        "cross_currency_basis_bps": -33,
        "vol_regime": "Stressed",
    }

    apply_control_patch(state_a, patch)
    apply_control_patch(state_b, patch)

    snap_a = snapshot_for_narrative(state_a)
    snap_b = snapshot_for_narrative(state_b)

    assert snap_a == snap_b
    assert snap_a["selected_scenario"] == "stress"
    assert state_a.market_forwards.equals(state_b.market_forwards)


TARGET_PAGES = [
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]


@pytest.mark.parametrize("target_page", TARGET_PAGES)
def test_navigation_preserves_session_keys_and_scenario_selection(target_page: str) -> None:
    canonical = init_market_state_from_generator(seed=33, vol_regime="Stressed")
    session_state = {
        "market_state": canonical,
        "selected_scenario": "stress",
        "scenario": "stress",
        "suggested_page": target_page,
        "custom_scenario_magnitude": 0.4,
        "base_rate": 4.0,
        "quote_rate": 6.5,
        "spot_fx": 370.0,
        "cross_currency_basis_bps": -40,
    }
    before_keys = set(session_state)

    _ = get_market_params(session_state)

    assert set(session_state).issuperset(before_keys)
    assert session_state["selected_scenario"] == "stress"
    assert session_state["suggested_page"] == target_page


def test_legacy_shallow_state_is_normalized_to_canonical_shape() -> None:
    session_state = {
        "market_state": {
            "spot_fx": 371.0,
            "base_rate": 4.9,
            "quote_rate": 6.8,
            "cross_currency_basis_bps": -32.0,
        }
    }
    canonical = normalize_session_market_state(session_state, seed=19)
    assert set(("seed", "regime", "base_snapshot", "stressed_snapshot", "scenario")).issubset(canonical.keys())
    assert session_state["market_state"] is canonical
