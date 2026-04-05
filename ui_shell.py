from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

import streamlit as st

from src.explainers.narratives import default_transmission_text, diff_state
from src.scenarios.scenario_library import SCENARIO_LIBRARY, apply_scenario

LEARNING_PATH = [
    "1. Start here",
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]


def _default_market_state() -> dict[str, Any]:
    return {
        "global": {
            "mode": "Basic",
            "user_role": "Treasurer",
            "valuation_date": date.today().isoformat(),
            "regime": "Normal",
            "selected_scenario": "None",
        },
        "market": {
            "spot": 1.08,
            "huf_curve": {"front": 7.00, "belly": 6.20, "back": 5.60},
            "usd_curve": {"front": 4.25, "belly": 4.10, "back": 3.95},
            "basis_curve_bps": {"front": -32.0, "belly": -22.0, "back": -15.0},
            "forward_override_bps": 0.0,
            "credit_funding_spread_levels_bps": {"credit": 55.0, "funding": 38.0},
        },
        "frictions": {
            "capital_charge_bps": 35.0,
            "funding_spread_bps": 40.0,
            "cva_fva_proxy_bps": 28.0,
            "clearing_enabled": True,
            "counterparty_quality": "A",
            "repo_liquidity_availability": "Normal",
            "balance_sheet_capacity": "Balanced",
        },
        "hedge": {
            "style": "Matched",
            "roll_tenor": "3m",
            "hedge_ratio": 1.00,
            "risk_aversion": 0.50,
        },
    }


def _sync_legacy_aliases() -> None:
    market_state = st.session_state.market_state
    st.session_state.mode = market_state["global"]["mode"]
    st.session_state.base_rate = float(market_state["market"]["usd_curve"]["front"])
    st.session_state.quote_rate = float(market_state["market"]["huf_curve"]["front"])
    st.session_state.spot_fx = float(market_state["market"]["spot"])
    st.session_state.cross_currency_basis_bps = int(round(market_state["market"]["basis_curve_bps"]["belly"]))
    st.session_state.vol_regime = market_state["global"]["regime"]


def _recompute_market_deterministic(previous_state: dict[str, Any]) -> None:
    current_state = st.session_state.market_state

    market = current_state["market"]
    frictions = current_state["frictions"]
    hedge = current_state["hedge"]

    avg_huf = sum(float(v) for v in market["huf_curve"].values()) / 3
    avg_usd = sum(float(v) for v in market["usd_curve"].values()) / 3
    avg_basis_bps = sum(float(v) for v in market["basis_curve_bps"].values()) / 3
    carry = avg_huf - avg_usd + avg_basis_bps / 100
    friction_bps = (
        float(frictions["capital_charge_bps"])
        + float(frictions["funding_spread_bps"])
        + float(frictions["cva_fva_proxy_bps"])
    )
    hedge_penalty = (1.0 - float(hedge["hedge_ratio"])) * 50 + float(hedge["risk_aversion"]) * 10

    st.session_state.market_metrics = {
        "carry_proxy_pct": round(carry, 6),
        "all_in_friction_bps": round(friction_bps, 2),
        "hedge_penalty_bps": round(hedge_penalty, 2),
        "net_pickup_bps": round(carry * 100 - friction_bps - hedge_penalty, 2),
    }

    changes = diff_state(previous_state, current_state)
    st.session_state.market_narrative = default_transmission_text(changes)
    st.session_state.market_signature = str(current_state)
    _sync_legacy_aliases()


def _update_state(path: tuple[str, ...], value: Any) -> None:
    previous_state = deepcopy(st.session_state.market_state)
    cursor = st.session_state.market_state
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    _recompute_market_deterministic(previous_state)


def _apply_selected_scenario() -> None:
    selected = st.session_state.market_state["global"]["selected_scenario"]
    if selected == "None":
        return

    previous_state = deepcopy(st.session_state.market_state)
    scenario = SCENARIO_LIBRARY[selected]

    base = {
        "huf_rates": deepcopy(st.session_state.market_state["market"]["huf_curve"]),
        "usd_rates": deepcopy(st.session_state.market_state["market"]["usd_curve"]),
        "spot": float(st.session_state.market_state["market"]["spot"]),
        "forward_points": float(st.session_state.market_state["market"]["forward_override_bps"]),
        "basis_curve": deepcopy(st.session_state.market_state["market"]["basis_curve_bps"]),
        "credit_spreads": {
            "sovereign": float(st.session_state.market_state["market"]["credit_funding_spread_levels_bps"]["credit"]),
            "banks": float(st.session_state.market_state["market"]["credit_funding_spread_levels_bps"]["credit"]),
        },
        "funding_spreads": {
            "secured": float(st.session_state.market_state["market"]["credit_funding_spread_levels_bps"]["funding"]),
            "unsecured": float(st.session_state.market_state["frictions"]["funding_spread_bps"]),
        },
        "capital_xva_proxy": float(st.session_state.market_state["frictions"]["cva_fva_proxy_bps"]),
        "liquidity_repo_availability": 0.0,
    }
    shocked = apply_scenario(scenario, base)

    ms = st.session_state.market_state
    ms["market"]["huf_curve"] = shocked["huf_rates"]
    ms["market"]["usd_curve"] = shocked["usd_rates"]
    ms["market"]["spot"] = shocked["spot"]
    ms["market"]["forward_override_bps"] = shocked["forward_points"]
    ms["market"]["basis_curve_bps"] = shocked["basis_curve"]
    ms["market"]["credit_funding_spread_levels_bps"]["credit"] = shocked["credit_spreads"]["sovereign"]
    ms["market"]["credit_funding_spread_levels_bps"]["funding"] = shocked["funding_spreads"]["secured"]
    ms["frictions"]["funding_spread_bps"] = shocked["funding_spreads"]["unsecured"]
    ms["frictions"]["cva_fva_proxy_bps"] = shocked["capital_xva_proxy"]

    _recompute_market_deterministic(previous_state)


def _reset_market_state() -> None:
    previous_state = deepcopy(st.session_state.market_state)
    st.session_state.market_state = _default_market_state()
    _recompute_market_deterministic(previous_state)


def _init_defaults() -> None:
    st.session_state.setdefault("market_state", _default_market_state())
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("market_narrative", "No state inputs changed; valuation and carry channels remain unchanged.")
    st.session_state.setdefault("market_metrics", {})
    st.session_state.setdefault("market_signature", "")
    _sync_legacy_aliases()


def render_global_shell() -> None:
    """Render grouped global/market/friction/hedge controls in the sidebar."""
    _init_defaults()

    ms = st.session_state.market_state

    with st.sidebar:
        st.header("Learning + Market Controls")

        st.subheader("1. Global")
        _update_state(("global", "mode"), st.segmented_control("Basic/Learning mode", ["Basic", "Learning"], default=ms["global"]["mode"]))
        _update_state(("global", "user_role"), st.selectbox("User role", ["Treasurer", "Trader", "Risk", "CIO"], index=["Treasurer", "Trader", "Risk", "CIO"].index(ms["global"]["user_role"])))
        _update_state(("global", "valuation_date"), st.date_input("Valuation date", value=date.fromisoformat(ms["global"]["valuation_date"])).isoformat())
        _update_state(("global", "regime"), st.selectbox("Regime selection", ["Calm", "Normal", "Stressed"], index=["Calm", "Normal", "Stressed"].index(ms["global"]["regime"])))

        scenario_options = ["None", *SCENARIO_LIBRARY.keys()]
        _update_state(("global", "selected_scenario"), st.selectbox("Scenario selection", scenario_options, index=scenario_options.index(ms["global"]["selected_scenario"])))
        scen_cols = st.columns(2)
        if scen_cols[0].button("Apply scenario"):
            _apply_selected_scenario()
        if scen_cols[1].button("Reset state"):
            _reset_market_state()

        st.subheader("2. Market")
        _update_state(("market", "spot"), st.number_input("Spot", min_value=0.1, max_value=1000.0, value=float(ms["market"]["spot"]), step=0.0001, format="%.4f"))

        st.caption("HUF curve (%)")
        huf_cols = st.columns(3)
        _update_state(("market", "huf_curve", "front"), huf_cols[0].number_input("HUF front", value=float(ms["market"]["huf_curve"]["front"]), step=0.05))
        _update_state(("market", "huf_curve", "belly"), huf_cols[1].number_input("HUF belly", value=float(ms["market"]["huf_curve"]["belly"]), step=0.05))
        _update_state(("market", "huf_curve", "back"), huf_cols[2].number_input("HUF back", value=float(ms["market"]["huf_curve"]["back"]), step=0.05))

        st.caption("USD curve (%)")
        usd_cols = st.columns(3)
        _update_state(("market", "usd_curve", "front"), usd_cols[0].number_input("USD front", value=float(ms["market"]["usd_curve"]["front"]), step=0.05))
        _update_state(("market", "usd_curve", "belly"), usd_cols[1].number_input("USD belly", value=float(ms["market"]["usd_curve"]["belly"]), step=0.05))
        _update_state(("market", "usd_curve", "back"), usd_cols[2].number_input("USD back", value=float(ms["market"]["usd_curve"]["back"]), step=0.05))

        st.caption("Basis curve (bps)")
        basis_cols = st.columns(3)
        _update_state(("market", "basis_curve_bps", "front"), basis_cols[0].number_input("Basis front", value=float(ms["market"]["basis_curve_bps"]["front"]), step=1.0))
        _update_state(("market", "basis_curve_bps", "belly"), basis_cols[1].number_input("Basis belly", value=float(ms["market"]["basis_curve_bps"]["belly"]), step=1.0))
        _update_state(("market", "basis_curve_bps", "back"), basis_cols[2].number_input("Basis back", value=float(ms["market"]["basis_curve_bps"]["back"]), step=1.0))

        _update_state(("market", "forward_override_bps"), st.number_input("Forward override (bps)", value=float(ms["market"]["forward_override_bps"]), step=1.0))
        cfs = ms["market"]["credit_funding_spread_levels_bps"]
        _update_state(("market", "credit_funding_spread_levels_bps", "credit"), st.number_input("Credit spread level (bps)", value=float(cfs["credit"]), step=1.0))
        _update_state(("market", "credit_funding_spread_levels_bps", "funding"), st.number_input("Funding spread level (bps)", value=float(cfs["funding"]), step=1.0))

        st.subheader("3. Frictions")
        _update_state(("frictions", "capital_charge_bps"), st.number_input("Capital charge (bps)", value=float(ms["frictions"]["capital_charge_bps"]), step=1.0))
        _update_state(("frictions", "funding_spread_bps"), st.number_input("Funding spread (bps)", value=float(ms["frictions"]["funding_spread_bps"]), step=1.0))
        _update_state(("frictions", "cva_fva_proxy_bps"), st.number_input("CVA/FVA proxy (bps)", value=float(ms["frictions"]["cva_fva_proxy_bps"]), step=1.0))
        _update_state(("frictions", "clearing_enabled"), st.toggle("Clearing toggle", value=bool(ms["frictions"]["clearing_enabled"])))
        _update_state(("frictions", "counterparty_quality"), st.selectbox("Counterparty quality", ["AA", "A", "BBB", "BB"], index=["AA", "A", "BBB", "BB"].index(ms["frictions"]["counterparty_quality"])))
        _update_state(("frictions", "repo_liquidity_availability"), st.selectbox("Repo/liquidity availability", ["Abundant", "Normal", "Tight"], index=["Abundant", "Normal", "Tight"].index(ms["frictions"]["repo_liquidity_availability"])))
        _update_state(("frictions", "balance_sheet_capacity"), st.selectbox("Balance-sheet capacity", ["Ample", "Balanced", "Constrained"], index=["Ample", "Balanced", "Constrained"].index(ms["frictions"]["balance_sheet_capacity"])))

        st.subheader("4. Hedge")
        _update_state(("hedge", "style"), st.radio("Matched vs rolling", ["Matched", "Rolling"], horizontal=True, index=["Matched", "Rolling"].index(ms["hedge"]["style"])))
        _update_state(("hedge", "roll_tenor"), st.segmented_control("Roll tenor", ["1m", "3m", "6m"], default=ms["hedge"]["roll_tenor"]))
        _update_state(("hedge", "hedge_ratio"), st.slider("Hedge ratio", min_value=0.0, max_value=1.5, value=float(ms["hedge"]["hedge_ratio"]), step=0.01))
        _update_state(("hedge", "risk_aversion"), st.slider("Risk aversion", min_value=0.0, max_value=1.0, value=float(ms["hedge"]["risk_aversion"]), step=0.01))

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")

        st.caption(st.session_state.market_narrative)


def learning_hint(text: str) -> None:
    if st.session_state.get("mode", "Basic") == "Learning":
        st.info(text)
