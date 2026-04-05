"""Scenario library for synthetic HUF/USD cross-currency basis analytics.

Each scenario defines a coherent vector of shocks across:
- HUF and USD rates (front/belly/back)
- FX spot and forward points
- basis curve
- credit and funding spreads
- capital/XVA proxy
- liquidity/repo availability
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict


ShockMap = Dict[str, Any]


@dataclass(frozen=True)
class Scenario:
    """Container for a named market scenario and its shock vector."""

    name: str
    description: str
    shocks: ShockMap

    def apply(self, base_state: ShockMap) -> ShockMap:
        """Return a shocked state by additive merge into a base synthetic state."""
        return apply_scenario(self, base_state)


def _additive_merge(base: Any, shock: Any) -> Any:
    """Recursively merge shock into base.

    Rules:
    - dict + dict: merge each key recursively.
    - numeric + numeric: additive (base + shock).
    - otherwise: shock overwrites base.
    """
    if isinstance(base, dict) and isinstance(shock, dict):
        merged = deepcopy(base)
        for key, shock_value in shock.items():
            if key in merged:
                merged[key] = _additive_merge(merged[key], shock_value)
            else:
                merged[key] = deepcopy(shock_value)
        return merged

    if isinstance(base, (int, float)) and isinstance(shock, (int, float)):
        return base + shock

    return deepcopy(shock)


def apply_scenario(scenario: Scenario, base_state: ShockMap) -> ShockMap:
    """Apply ``scenario`` shocks to ``base_state`` via additive merge."""
    return _additive_merge(base_state, scenario.shocks)


def calm_baseline() -> Scenario:
    return Scenario(
        name="calm_baseline",
        description="Low-volatility carry environment with balanced liquidity.",
        shocks={
            "huf_rates": {"front": -0.05, "belly": -0.03, "back": -0.01},
            "usd_rates": {"front": -0.02, "belly": -0.01, "back": 0.00},
            "spot": 0.00,
            "forward_points": -0.10,
            "basis_curve": {"front": 1.0, "belly": 0.5, "back": 0.2},
            "credit_spreads": {"sovereign": -2.0, "banks": -3.0},
            "funding_spreads": {"secured": -1.0, "unsecured": -2.0},
            "capital_xva_proxy": -0.5,
            "liquidity_repo_availability": 2.0,
        },
    )


def capital_outflow_shock() -> Scenario:
    return Scenario(
        name="capital_outflow_shock",
        description="Foreign capital exits local assets, pressuring HUF and local funding.",
        shocks={
            "huf_rates": {"front": 0.90, "belly": 0.70, "back": 0.45},
            "usd_rates": {"front": 0.10, "belly": 0.08, "back": 0.05},
            "spot": 4.50,
            "forward_points": 7.00,
            "basis_curve": {"front": -9.0, "belly": -6.0, "back": -3.0},
            "credit_spreads": {"sovereign": 25.0, "banks": 35.0},
            "funding_spreads": {"secured": 12.0, "unsecured": 22.0},
            "capital_xva_proxy": 16.0,
            "liquidity_repo_availability": -18.0,
        },
    )


def currency_devaluation_shock() -> Scenario:
    return Scenario(
        name="currency_devaluation_shock",
        description="Abrupt HUF weakening with inflation and risk-premium repricing.",
        shocks={
            "huf_rates": {"front": 1.20, "belly": 0.95, "back": 0.60},
            "usd_rates": {"front": 0.05, "belly": 0.04, "back": 0.03},
            "spot": 8.00,
            "forward_points": 12.0,
            "basis_curve": {"front": -7.0, "belly": -5.0, "back": -2.0},
            "credit_spreads": {"sovereign": 20.0, "banks": 28.0},
            "funding_spreads": {"secured": 10.0, "unsecured": 18.0},
            "capital_xva_proxy": 12.0,
            "liquidity_repo_availability": -12.0,
        },
    )


def sovereign_downgrade_liquidity_shock() -> Scenario:
    return Scenario(
        name="sovereign_downgrade_liquidity_shock",
        description="Rating downgrade triggers spread widening and liquidity withdrawal.",
        shocks={
            "huf_rates": {"front": 0.75, "belly": 0.85, "back": 0.95},
            "usd_rates": {"front": 0.06, "belly": 0.10, "back": 0.12},
            "spot": 3.25,
            "forward_points": 6.50,
            "basis_curve": {"front": -6.0, "belly": -8.0, "back": -9.0},
            "credit_spreads": {"sovereign": 45.0, "banks": 30.0},
            "funding_spreads": {"secured": 14.0, "unsecured": 26.0},
            "capital_xva_proxy": 20.0,
            "liquidity_repo_availability": -24.0,
        },
    )


def usd_funding_shortage() -> Scenario:
    return Scenario(
        name="usd_funding_shortage",
        description="Acute USD scarcity drives front-end USD rates and basis stress.",
        shocks={
            "huf_rates": {"front": 0.20, "belly": 0.15, "back": 0.10},
            "usd_rates": {"front": 1.10, "belly": 0.70, "back": 0.35},
            "spot": 2.00,
            "forward_points": 9.50,
            "basis_curve": {"front": -18.0, "belly": -10.0, "back": -4.0},
            "credit_spreads": {"sovereign": 10.0, "banks": 22.0},
            "funding_spreads": {"secured": 20.0, "unsecured": 34.0},
            "capital_xva_proxy": 14.0,
            "liquidity_repo_availability": -20.0,
        },
    )


def central_bank_divergence() -> Scenario:
    return Scenario(
        name="central_bank_divergence",
        description="Policy paths diverge: HUF easing while USD stays restrictive.",
        shocks={
            "huf_rates": {"front": -0.80, "belly": -0.45, "back": -0.15},
            "usd_rates": {"front": 0.45, "belly": 0.30, "back": 0.15},
            "spot": 2.75,
            "forward_points": 4.00,
            "basis_curve": {"front": -5.0, "belly": -3.0, "back": -1.0},
            "credit_spreads": {"sovereign": 6.0, "banks": 8.0},
            "funding_spreads": {"secured": 5.0, "unsecured": 9.0},
            "capital_xva_proxy": 5.0,
            "liquidity_repo_availability": -6.0,
        },
    )


def basis_normalisation() -> Scenario:
    return Scenario(
        name="basis_normalisation",
        description="Cross-currency basis mean-reverts as funding pressures fade.",
        shocks={
            "huf_rates": {"front": -0.10, "belly": -0.05, "back": -0.02},
            "usd_rates": {"front": -0.05, "belly": -0.03, "back": -0.01},
            "spot": -0.50,
            "forward_points": -5.00,
            "basis_curve": {"front": 10.0, "belly": 6.0, "back": 3.0},
            "credit_spreads": {"sovereign": -5.0, "banks": -8.0},
            "funding_spreads": {"secured": -7.0, "unsecured": -12.0},
            "capital_xva_proxy": -8.0,
            "liquidity_repo_availability": 14.0,
        },
    )


def global_risk_off() -> Scenario:
    return Scenario(
        name="global_risk_off",
        description="Risk aversion shock with broad spread widening and weaker EMFX.",
        shocks={
            "huf_rates": {"front": 0.55, "belly": 0.40, "back": 0.25},
            "usd_rates": {"front": -0.15, "belly": -0.10, "back": -0.05},
            "spot": 5.00,
            "forward_points": 8.00,
            "basis_curve": {"front": -12.0, "belly": -8.0, "back": -4.0},
            "credit_spreads": {"sovereign": 30.0, "banks": 32.0},
            "funding_spreads": {"secured": 11.0, "unsecured": 20.0},
            "capital_xva_proxy": 18.0,
            "liquidity_repo_availability": -22.0,
        },
    )


def local_disinflation_relief() -> Scenario:
    return Scenario(
        name="local_disinflation_relief",
        description="Disinflation allows local rates and spreads to compress.",
        shocks={
            "huf_rates": {"front": -1.10, "belly": -0.75, "back": -0.40},
            "usd_rates": {"front": -0.08, "belly": -0.05, "back": -0.02},
            "spot": -3.00,
            "forward_points": -6.00,
            "basis_curve": {"front": 4.0, "belly": 3.0, "back": 2.0},
            "credit_spreads": {"sovereign": -18.0, "banks": -20.0},
            "funding_spreads": {"secured": -8.0, "unsecured": -14.0},
            "capital_xva_proxy": -10.0,
            "liquidity_repo_availability": 12.0,
        },
    )


def custom_parallel(
    *,
    huf_shift: float = 0.0,
    usd_shift: float = 0.0,
    spot_shift: float = 0.0,
    forward_points_shift: float = 0.0,
    basis_shift: float = 0.0,
    credit_shift: float = 0.0,
    funding_shift: float = 0.0,
    capital_xva_shift: float = 0.0,
    liquidity_shift: float = 0.0,
) -> Scenario:
    """Build a custom scenario with parallel shifts by risk bucket."""
    return Scenario(
        name="custom_parallel",
        description="User-defined parallel shifts across all curve buckets.",
        shocks={
            "huf_rates": {"front": huf_shift, "belly": huf_shift, "back": huf_shift},
            "usd_rates": {"front": usd_shift, "belly": usd_shift, "back": usd_shift},
            "spot": spot_shift,
            "forward_points": forward_points_shift,
            "basis_curve": {"front": basis_shift, "belly": basis_shift, "back": basis_shift},
            "credit_spreads": {"sovereign": credit_shift, "banks": credit_shift},
            "funding_spreads": {"secured": funding_shift, "unsecured": funding_shift},
            "capital_xva_proxy": capital_xva_shift,
            "liquidity_repo_availability": liquidity_shift,
        },
    )


def custom_steepener(
    *,
    huf_front: float = -0.20,
    huf_belly: float = 0.00,
    huf_back: float = 0.25,
    usd_front: float = -0.10,
    usd_belly: float = 0.00,
    usd_back: float = 0.15,
    basis_front: float = 2.0,
    basis_belly: float = 0.0,
    basis_back: float = -2.0,
    spot_shift: float = 0.0,
    forward_points_shift: float = 0.0,
    credit_shift: float = 0.0,
    funding_shift: float = 0.0,
    capital_xva_shift: float = 0.0,
    liquidity_shift: float = 0.0,
) -> Scenario:
    """Build a custom steepener (front down / back up) scenario."""
    return Scenario(
        name="custom_steepener",
        description="User-defined steepener for HUF/USD and basis curves.",
        shocks={
            "huf_rates": {"front": huf_front, "belly": huf_belly, "back": huf_back},
            "usd_rates": {"front": usd_front, "belly": usd_belly, "back": usd_back},
            "spot": spot_shift,
            "forward_points": forward_points_shift,
            "basis_curve": {"front": basis_front, "belly": basis_belly, "back": basis_back},
            "credit_spreads": {"sovereign": credit_shift, "banks": credit_shift},
            "funding_spreads": {"secured": funding_shift, "unsecured": funding_shift},
            "capital_xva_proxy": capital_xva_shift,
            "liquidity_repo_availability": liquidity_shift,
        },
    )


def custom_flattener(
    *,
    huf_front: float = 0.25,
    huf_belly: float = 0.00,
    huf_back: float = -0.20,
    usd_front: float = 0.15,
    usd_belly: float = 0.00,
    usd_back: float = -0.10,
    basis_front: float = -2.0,
    basis_belly: float = 0.0,
    basis_back: float = 2.0,
    spot_shift: float = 0.0,
    forward_points_shift: float = 0.0,
    credit_shift: float = 0.0,
    funding_shift: float = 0.0,
    capital_xva_shift: float = 0.0,
    liquidity_shift: float = 0.0,
) -> Scenario:
    """Build a custom flattener (front up / back down) scenario."""
    return Scenario(
        name="custom_flattener",
        description="User-defined flattener for HUF/USD and basis curves.",
        shocks={
            "huf_rates": {"front": huf_front, "belly": huf_belly, "back": huf_back},
            "usd_rates": {"front": usd_front, "belly": usd_belly, "back": usd_back},
            "spot": spot_shift,
            "forward_points": forward_points_shift,
            "basis_curve": {"front": basis_front, "belly": basis_belly, "back": basis_back},
            "credit_spreads": {"sovereign": credit_shift, "banks": credit_shift},
            "funding_spreads": {"secured": funding_shift, "unsecured": funding_shift},
            "capital_xva_proxy": capital_xva_shift,
            "liquidity_repo_availability": liquidity_shift,
        },
    )


SCENARIO_LIBRARY: Dict[str, Scenario] = {
    "calm_baseline": calm_baseline(),
    "capital_outflow_shock": capital_outflow_shock(),
    "currency_devaluation_shock": currency_devaluation_shock(),
    "sovereign_downgrade_liquidity_shock": sovereign_downgrade_liquidity_shock(),
    "usd_funding_shortage": usd_funding_shortage(),
    "central_bank_divergence": central_bank_divergence(),
    "basis_normalisation": basis_normalisation(),
    "global_risk_off": global_risk_off(),
    "local_disinflation_relief": local_disinflation_relief(),
}


__all__ = [
    "Scenario",
    "SCENARIO_LIBRARY",
    "apply_scenario",
    "calm_baseline",
    "capital_outflow_shock",
    "currency_devaluation_shock",
    "sovereign_downgrade_liquidity_shock",
    "usd_funding_shortage",
    "central_bank_divergence",
    "basis_normalisation",
    "global_risk_off",
    "local_disinflation_relief",
    "custom_parallel",
    "custom_steepener",
    "custom_flattener",
]
