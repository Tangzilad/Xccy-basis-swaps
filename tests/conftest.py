from __future__ import annotations

import copy

import pytest


@pytest.fixture
def base_snapshot() -> dict:
    """Deterministic baseline market-state snapshot for tests."""
    return {
        "huf_rates": {"front": 0.072, "belly": 0.069, "back": 0.065},
        "usd_rates": {"front": 0.051, "belly": 0.047, "back": 0.043},
        "spot": 365.0,
        "forward_points": 6.2,
        "basis_curve": {"front": -26.0, "belly": -18.0, "back": -11.0},
        "credit_spreads": {"sovereign": 80.0, "banks": 115.0},
        "funding_spreads": {"secured": 42.0, "unsecured": 66.0},
        "capital_xva_proxy": 34.0,
        "liquidity_repo_availability": 55.0,
    }


@pytest.fixture
def stress_snapshot(base_snapshot: dict) -> dict:
    """Deterministic stressed snapshot derived from baseline."""
    stressed = copy.deepcopy(base_snapshot)
    stressed["huf_rates"] = {"front": 0.087, "belly": 0.081, "back": 0.076}
    stressed["usd_rates"] = {"front": 0.057, "belly": 0.053, "back": 0.049}
    stressed["spot"] = 379.5
    stressed["forward_points"] = 15.8
    stressed["basis_curve"] = {"front": -44.0, "belly": -31.0, "back": -20.0}
    stressed["credit_spreads"] = {"sovereign": 104.0, "banks": 149.0}
    stressed["funding_spreads"] = {"secured": 63.0, "unsecured": 94.0}
    stressed["capital_xva_proxy"] = 51.0
    stressed["liquidity_repo_availability"] = 31.0
    return stressed
