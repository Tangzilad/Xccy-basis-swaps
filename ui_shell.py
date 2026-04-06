from __future__ import annotations

import streamlit as st

from src.controllers.market_state_controller import (
    SCENARIO_LIBRARY,
    apply_state_scenario,
    build_custom_scenario,
    clip_regime,
    regenerate_market_state,
)
from src.state.session_access import get_canonical_market_context
    ensure_market_state,
    regenerate_market_state,
    summarize_for_shell,
)
    make_stress_table,
    regenerate_market_state,
    summarize_for_shell,
)
from src.explainers.narratives import ExplanationSpec, explain_transition_dict

LEARNING_PATH = [
    "1. Start here",
    "2. XCCY mechanics",
    "3. Parity lab",
    "4. Market basis and funding transformation",
    "5. Persistence / XVA / arbitrage limits",
    "6. Hedged pickup and hedge choice",
    "7. HUF/USD strategy and stress lab",
]

SCENARIO_OPTIONS = {
    "none": "No scenario",
    "parallel_up": "Parallel up",
    "parallel_down": "Parallel down",
    "steepener": "Steepener",
    "flattener": "Flattener",
    "funding_stress": "Funding stress",
    "credit_widening": "Credit widening",
    "liquidity_crunch": "Liquidity crunch",
    "custom_parallel": "Custom parallel",
    "custom_steepener": "Custom steepener",
    "custom_flattener": "Custom flattener",
}


def _apply_curve_controls(*, base_snapshot: dict, spot_fx: float, usd_rate_pct: float, huf_rate_pct: float, basis_bps: float) -> dict:
    out = deepcopy(base_snapshot)
    usd_curve = out["usd_curve_df"]
    huf_curve = out["huf_curve_df"]
    basis_curve = out["basis_curve_df"]

    one_y = "1Y"
    usd_idx = usd_curve["tenor"] == one_y
    huf_idx = huf_curve["tenor"] == one_y
    basis_idx = basis_curve["tenor"] == one_y

    if usd_idx.any():
        target = float(usd_rate_pct) / 100.0
        shift = target - float(usd_curve.loc[usd_idx, "usd_zero_rate"].iloc[0])
        usd_curve.loc[:, "usd_zero_rate"] = usd_curve["usd_zero_rate"] + shift

    if huf_idx.any():
        target = float(huf_rate_pct) / 100.0
        shift = target - float(huf_curve.loc[huf_idx, "huf_zero_rate"].iloc[0])
        huf_curve.loc[:, "huf_zero_rate"] = huf_curve["huf_zero_rate"] + shift

    if basis_idx.any():
        shift = float(basis_bps) - float(basis_curve.loc[basis_idx, "basis_bps"].iloc[0])
        basis_curve.loc[:, "basis_bps"] = basis_curve["basis_bps"] + shift
        basis_curve.loc[:, "implied_basis_decimal"] = basis_curve["basis_bps"] / 1e4

    out["spot_fx"] = float(spot_fx)

    years = out["basis_curve_df"]["years"].to_numpy(dtype=float)
    basis = out["basis_curve_df"]["basis_bps"].to_numpy(dtype=float)
    credit = out["credit_assumptions"]["credit_spread_bps"].to_numpy(dtype=float)
    fric = out["friction_assumptions"]["funding_friction_bps"].to_numpy(dtype=float)
    theo = out["theoretical_forward_df"]["theoretical_forward"].to_numpy(dtype=float)
    out["market_forward_df"]["market_forward"] = theo * __import__("numpy").exp((basis + credit + fric) / 1e4 * years)
    return out


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_seed", 7)
    st.session_state.setdefault("mode", "Basic")
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("selected_scenario", "none")
    st.session_state.setdefault("custom_scenario_magnitude", 0.5)
    st.session_state.setdefault("market_narrative", "Canonical market state drives all pages.")
    get_canonical_market_context(st.session_state, seed=int(st.session_state.market_seed))

SCENARIO_OPTIONS = {
    "none": "No scenario",
    **{name: name.replace("_", " ").title() for name in SCENARIO_LIBRARY},
    "custom_parallel": "Custom Parallel",
    "custom_steepener": "Custom Steepener",
    "custom_flattener": "Custom Flattener",
}



# Keep smoke-test stubs and cold imports resilient.
try:
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
except Exception:
    pass


def _button(label: str) -> bool:
    button_fn = getattr(st, "button", None)
    if callable(button_fn):
        return bool(button_fn(label))
    return False

def _sync_legacy_fields() -> None:
    summary = summarize_for_shell(st.session_state.market_state["base_snapshot"])
    st.session_state.base_rate = summary["base_rate"]
    st.session_state.quote_rate = summary["quote_rate"]
    st.session_state.spot_fx = summary["spot_fx"]
    st.session_state.cross_currency_basis_bps = int(round(summary["cross_currency_basis_bps"]))
    st.session_state.vol_regime = "Normal"

    # Legacy keys used by lesson pages.
    st.session_state.market_state["usd_rate"] = summary["base_rate"] / 100.0
    st.session_state.market_state["huf_rate"] = summary["quote_rate"] / 100.0
    st.session_state.market_state["basis_bps"] = summary["cross_currency_basis_bps"]
    st.session_state.market_state["spot_fx"] = summary["spot_fx"]


def ensure_market_state_initialized() -> None:
    defaults = {
        "mode": "Basic",
        "base_rate": 4.25,
        "quote_rate": 5.0,
        "spot_fx": 365.0,
        "cross_currency_basis_bps": -22,
        "vol_regime": "Normal",
        "suggested_page": LEARNING_PATH[0],
        "market_seed": 7,
        "custom_scenario_magnitude": 0.25,
        "selected_scenario": "none",
        "market_narrative": "Use sidebar controls to regenerate markets and apply scenarios.",
        "active_role": "treasury",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    st.session_state.market_state = ensure_market_state(
        st.session_state.get("market_state"), seed=st.session_state.market_seed
    )
    _sync_legacy_fields()


    "calm_baseline": "Calm baseline",
    "capital_outflow_shock": "Capital outflow shock",
    "currency_devaluation_shock": "Currency devaluation shock",
    "sovereign_downgrade_liquidity_shock": "Sovereign downgrade + liquidity shock",
    "usd_funding_shortage": "USD funding shortage",
    "central_bank_divergence": "Central bank divergence",
    "basis_normalisation": "Basis normalisation",
    "global_risk_off": "Global risk-off",
    "local_disinflation_relief": "Local disinflation relief",
    "custom_parallel": "Custom parallel",
    "custom_steepener": "Custom steepener",
    "custom_flattener": "Custom flattener",
}

EXPLANATION_INCLUDE_KEYS = {
    "mechanics": ["spot_fx", "base_rate", "quote_rate", "cross_currency_basis_bps", "vol_regime"],
    "parity": ["base_rate", "quote_rate", "spot_fx", "cross_currency_basis_bps", "vol_regime"],
    "funding": ["cross_currency_basis_bps", "base_rate", "quote_rate", "vol_regime"],
    "frictions": ["cross_currency_basis_bps", "vol_regime", "base_rate", "quote_rate"],
    "hedge": ["cross_currency_basis_bps", "spot_fx", "vol_regime", "quote_rate", "base_rate"],
    "stress": ["vol_regime", "cross_currency_basis_bps", "spot_fx", "base_rate", "quote_rate"],
    "overview": ["base_rate", "quote_rate", "spot_fx", "cross_currency_basis_bps", "vol_regime"],
}


def _scenario_from_selection(scenario_name: str):
    if scenario_name in SCENARIO_LIBRARY:
        return SCENARIO_LIBRARY[scenario_name]
    if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
        return build_custom_scenario(scenario_name, float(st.session_state.custom_scenario_magnitude))
    return None


def render_global_shell(*, page_context: str = "overview") -> None:
    _ = page_context
    ensure_market_state_initialized()
    context = get_canonical_market_context(st.session_state, seed=int(st.session_state.market_seed))
    state = context["state"]
    base_summary = context["summary_1y"]["base"]
def _vol_regime_from_market_state(state: dict[str, object]) -> str:
    regime_name = str(state.get("regime", {}).get("name", "baseline"))
    mapper = {"calm": "Calm", "stress": "Stressed", "baseline": "Normal"}
    return mapper.get(regime_name, "Normal")


def _sync_sidebar_from_base_snapshot() -> None:
    state = st.session_state["market_state"]
    shell_view = summarize_for_shell(state["base_snapshot"])
    st.session_state.base_rate = float(shell_view["base_rate"])
    st.session_state.quote_rate = float(shell_view["quote_rate"])
    st.session_state.spot_fx = float(shell_view["spot_fx"])
    st.session_state.cross_currency_basis_bps = int(round(float(shell_view["cross_currency_basis_bps"])))
    st.session_state.vol_regime = _vol_regime_from_market_state(state)


def ensure_market_state_initialized() -> None:
    st.session_state.setdefault("market_seed", 7)
    st.session_state["market_state"] = ensure_market_state(
        st.session_state.get("market_state"),
        seed=int(st.session_state.market_seed),
    )

    st.session_state.setdefault("selected_scenario", "none")
    st.session_state.setdefault("custom_scenario_magnitude", 0.5)
    st.session_state.setdefault("active_role", ROLE_OPTIONS[0])
    st.session_state.setdefault("mode", "Learning")
    st.session_state.setdefault("latest_transition_narrative", {})
    st.session_state.setdefault("market_narrative", "")
    st.session_state.setdefault("suggested_page", LEARNING_PATH[0])
    st.session_state.setdefault("previous_snapshot", {})

    _sync_sidebar_from_base_snapshot()


def _capture_snapshot() -> dict[str, object]:
    return {
        "mode": st.session_state.mode,
        "base_rate": float(st.session_state.base_rate),
        "quote_rate": float(st.session_state.quote_rate),
        "spot_fx": float(st.session_state.spot_fx),
        "cross_currency_basis_bps": int(st.session_state.cross_currency_basis_bps),
        "vol_regime": st.session_state.vol_regime,
        "active_role": st.session_state.active_role,
    }


def _build_spec(page_context: str) -> ExplanationSpec:
    context = page_context if page_context in EXPLANATION_INCLUDE_KEYS else "overview"
    specs: dict[str, ExplanationSpec] = {
        "mechanics": ExplanationSpec(
            transmission_template="Mechanics update propagates from policy-rate differential and basis into the synthetic term curve and carry profile.",
            economic_channel="Spot, rates, and basis jointly define where forward-implied funding deviates from covered parity anchors.",
            role_interpretations={
                "issuer": "Re-check issuance currency choice when transformed all-in cost moves.",
                "investor": "Map hedge-adjusted return drift versus unhedged carry temptation.",
                "treasury": "Track if internal transfer-pricing assumptions still align to external swap marks.",
                "arbitrageur": "Focus on whether the repricing widens or narrows executable dislocations.",
                "default": "Use the new curve shape as the baseline for downstream pages.",
            },
            inspect_next="Inspect tenor slope changes first; then verify whether near-end basis is driving most of the move.",
            mechanism_formula="F/S ≈ (1+r_quote)/(1+r_base) with basis wedge adjustments",
        ),
        "parity": ExplanationSpec(
            transmission_template="Parity lab recomputes implied forwards from the updated rate differential and basis wedge before comparing execution-adjusted carry.",
            economic_channel="Covered parity tension rises when basis and frictions offset nominal carry spread.",
            role_interpretations={
                "issuer": "Parity slippage can raise synthetic foreign-currency funding cost despite stable coupons.",
                "investor": "Treat widening parity gaps as a warning that hedge carry may decay faster than headline yield.",
                "treasury": "Use parity diagnostics to challenge transfer-price assumptions across desks.",
                "arbitrageur": "Screen whether observed gaps exceed balance-sheet and execution break-even thresholds.",
            },
            inspect_next="Inspect the shortest and mid tenors for parity breakdown persistence.",
            mechanism_formula="CIP gap ≈ implied forward - covered forward (basis-adjusted)",
        ),
        "funding": ExplanationSpec(
            transmission_template="Funding transformation view updates the basis curve and translates it into synthetic cross-currency funding pressure.",
            economic_channel="More negative basis signals stronger demand to borrow one currency via swaps, steepening transformation costs.",
            role_interpretations={
                "issuer": "Prioritize markets where swapped-back funding remains below direct issuance alternatives.",
                "investor": "Demand higher asset spread when transformation cost erodes hedge-adjusted pickup.",
                "treasury": "Rebalance collateral and term mix where funding pressure concentrates.",
                "arbitrageur": "Look for segments where funding scarcity appears over-priced relative to nearby tenors.",
            },
            inspect_next="Inspect front-end basis depth versus long-end normalization to locate funding bottlenecks.",
            mechanism_formula="All-in transformed cost ≈ local funding + basis + execution spread",
        ),
        "frictions": ExplanationSpec(
            transmission_template="Frictions page reruns persistence diagnostics with updated basis and volatility regime assumptions.",
            economic_channel="XVA, capital usage, and liquidity constraints slow arbitrage convergence even when raw spread signals look attractive.",
            role_interpretations={
                "issuer": "Treat persistent dislocations as potentially structural, not instantly mean-reverting.",
                "investor": "Scale expected pickup by persistence and implementation drag, not just spot spread.",
                "treasury": "Allocate scarce balance sheet to trades with strongest risk-adjusted convergence.",
                "arbitrageur": "Convergence speed matters as much as mispricing size when capital is binding.",
            },
            inspect_next="Inspect mid-curve persistence and volatility-regime changes for signs of slower convergence.",
            mechanism_formula="Net arb PnL ≈ gross basis gap - (XVA + capital + liquidity costs)",
        ),
        "hedge": ExplanationSpec(
            transmission_template="Hedge-choice analytics refresh all-in pickup after applying the new carry and basis inputs.",
            economic_channel="Instrument selection changes realized pickup via rollover risk, liquidity premium, and accounting constraints.",
            role_interpretations={
                "issuer": "Compare swap-vs-forward hedge paths against debt maturity and covenant limits.",
                "investor": "Favor hedge structures whose carry survives stressed liquidity assumptions.",
                "treasury": "Align hedge tenor and instrument to policy limits and liquidity buffers.",
                "arbitrageur": "Exploit divergence only where hedge implementation cost is reliably bounded.",
            },
            inspect_next="Inspect long-tenor pickup sensitivity to basis and volatility regime before sizing hedges.",
            mechanism_formula="Hedged pickup ≈ carry differential + basis adjustment - hedge cost",
        ),
        "stress": ExplanationSpec(
            transmission_template="Stress lab applies the updated controls as a new scenario anchor and recomputes tail basis sensitivity.",
            economic_channel="Volatility and basis shocks interact nonlinearly, amplifying drawdown and liquidity risk in stressed states.",
            role_interpretations={
                "issuer": "Plan contingency funding if stressed transformed costs breach budget tolerances.",
                "investor": "Demand stress-tested pickup, not base-case carry, before committing risk.",
                "treasury": "Use stress outputs to calibrate liquidity reserves and escalation triggers.",
                "arbitrageur": "Only deploy capital where stress paths still preserve exit liquidity.",
            },
            inspect_next="Inspect worst-tenor tail values and then test robustness under alternate role assumptions.",
            mechanism_formula="Tail impact ≈ max |basis_tenor| × stress multiplier",
        ),
        "overview": ExplanationSpec(
            transmission_template="Global controls updated the shared market state for all lesson pages.",
            economic_channel="Every downstream metric inherits this market-state anchor through carry, basis, and volatility channels.",
            role_interpretations={
                "issuer": "Monitor whether shared assumptions still support issuance and swap-back decisions.",
                "investor": "Use the new state as your baseline for hedge-adjusted return comparisons.",
                "treasury": "Treat this as the current house view feeding all page-level diagnostics.",
                "arbitrageur": "Use this baseline to scan where model-implied dislocations might open.",
            },
            inspect_next="Inspect the next lesson page to validate how the same state propagates into its local metrics.",
        ),
    }
    return specs[context]


def render_global_shell(*, page_context: str = "overview") -> None:
    """Render shared controls and a persistent suggested learning path."""
    _ = page_context
    ensure_market_state_initialized()
    state = st.session_state["market_state"]

    with st.sidebar:
        st.header("Learning + Market Controls")
        st.session_state.mode = st.segmented_control(
            "Mode", options=["Basic", "Learning"], default=st.session_state.mode
            "Mode",
            options=["Basic", "Learning"],
            default=st.session_state.mode,
            help="Basic simplifies narrative. Learning adds rationale and extra interpretation.",
        )

        st.subheader("Regime generator")
        st.session_state.market_seed = int(
            st.number_input("Seed", min_value=0, max_value=999_999, value=int(st.session_state.market_seed), step=1)
        )

        regime = st.session_state.market_state["regime"]
        st.subheader("Global market-state controls")
        base_rate = st.slider("Base currency policy rate (%)", 0.0, 12.0, float(base_summary["usd_rate"] * 100.0), 0.05)
        quote_rate = st.slider("Quote currency policy rate (%)", 0.0, 15.0, float(base_summary["huf_rate"] * 100.0), 0.05)
        spot_fx = st.number_input("Spot FX", min_value=120.0, max_value=1200.0, value=float(base_summary["spot_fx"]), step=0.01)
        basis_bps = st.slider("Cross-currency basis (bps)", -250, 250, int(round(float(base_summary["basis_bps"]))), 1)

        if st.button("Apply global controls"):
            state["base_snapshot"] = _apply_curve_controls(
                base_snapshot=state["base_snapshot"],
                spot_fx=float(spot_fx),
                usd_rate_pct=float(base_rate),
                huf_rate_pct=float(quote_rate),
                basis_bps=float(basis_bps),
            )
            state["stressed_snapshot"] = deepcopy(state["base_snapshot"])
            state["scenario"] = "none"
            st.session_state.market_state = state

        regime = st.session_state.market_state["regime"]
        st.subheader("Regime controls")
        st.session_state.base_rate = st.slider(
            "Base currency policy rate (%)", 0.0, 12.0, float(st.session_state.base_rate), 0.05
        )
        st.session_state.quote_rate = st.slider(
            "Quote currency policy rate (%)", 0.0, 15.0, float(st.session_state.quote_rate), 0.05
        )
        st.session_state.spot_fx = st.number_input(
            "Spot FX", min_value=120.0, max_value=1200.0, value=float(st.session_state.spot_fx), step=0.0001
        )
        st.session_state.cross_currency_basis_bps = st.slider(
            "Cross-currency basis (bps)", -250, 250, int(st.session_state.cross_currency_basis_bps), 1
        )
        st.session_state.vol_regime = st.selectbox(
            "Volatility regime",
            ["Calm", "Normal", "Stressed"],
            index=["Calm", "Normal", "Stressed"].index(str(st.session_state.vol_regime)),
        )

        st.session_state.active_role = st.selectbox(
            "Interpretation role",
            options=ROLE_OPTIONS,
            index=ROLE_OPTIONS.index(st.session_state.active_role),
            help="Narrative interpretation will adapt to this desk perspective.",
        )

        previous_snapshot = st.session_state.get("previous_snapshot") or _capture_snapshot()
        current_snapshot = _capture_snapshot()
        spec = _build_spec(page_context)
        include_keys = EXPLANATION_INCLUDE_KEYS.get(page_context, EXPLANATION_INCLUDE_KEYS["overview"])
        transition_payload = explain_transition_dict(
            previous_state=previous_snapshot,
            current_state=current_snapshot,
            role=st.session_state.active_role,
            spec=spec,
            include_keys=include_keys,
        )
        st.session_state.latest_transition_narrative = transition_payload

        st.divider()
        st.subheader("State-transition commentary")
        changed_inputs = transition_payload.get("changed_inputs", [])
        if changed_inputs:
            for change in changed_inputs:
                st.write(f"• {change['name']}: {change['previous']} → {change['current']}")
        else:
            st.write("• No included inputs changed in this transition.")
        st.caption(f"Transmission: {transition_payload['transmission_mechanism']}")
        st.caption(f"Economic channel: {transition_payload['economic_channel']}")
        st.caption(f"Role ({st.session_state.active_role}): {transition_payload['role_interpretation']}")
        st.caption(f"Inspect next: {transition_payload['inspect_next']}")

        regime = state["regime"]
        regime_name = st.selectbox("Regime preset", ["baseline", "calm", "stress"], index=0)
        level = st.slider("Level", -2.0, 2.0, float(regime.get("level", 0.0)), 0.05)
        slope = st.slider("Slope", -2.0, 2.0, float(regime.get("slope", 0.0)), 0.05)
        curvature = st.slider("Curvature", -2.0, 2.0, float(regime.get("curvature", 0.0)), 0.05)
        noise_scale = st.slider("Volatility / noise", 0.2, 3.0, float(regime.get("noise_scale", 1.0)), 0.05)
        liquidity = st.slider("Liquidity", 0.4, 2.0, float(regime.get("liquidity", 1.0)), 0.05)

        if st.button("Regenerate market"):
            st.session_state.market_state["seed"] = int(st.session_state.market_seed)
        if _button("Regenerate market"):
            st.session_state.market_state["seed"] = st.session_state.market_seed
            st.session_state.market_state["regime"] = clip_regime(
                {
                    "name": regime_name,
                    "level": level,
                    "slope": slope,
                    "curvature": curvature,
                    "noise_scale": noise_scale,
                    "liquidity": liquidity,
                }
            )
            st.session_state.market_state = regenerate_market_state(st.session_state.market_state)
            _sync_legacy_fields()
        if st.button("Regenerate market"):
            updated_state = {
                **state,
                "seed": int(st.session_state.market_seed),
                "regime": clip_regime(
                    {
                        "name": regime_name,
                        "level": level,
                        "slope": slope,
                        "curvature": curvature,
                        "noise_scale": noise_scale,
                        "liquidity": liquidity,
                    }
                ),
            }
            st.session_state.market_state = regenerate_market_state(updated_state)
            state = st.session_state.market_state
            _sync_sidebar_from_base_snapshot()

        st.subheader("Scenario selector")
        selected_label = SCENARIO_OPTIONS.get(st.session_state.selected_scenario, "No scenario")
        scenario_label = st.selectbox(
            "Scenario",
            list(SCENARIO_OPTIONS.values()),
            index=list(SCENARIO_OPTIONS.values()).index(selected_label),
        )
        all_labels = list(SCENARIO_OPTIONS.values())
        scenario_label = st.selectbox("Scenario", all_labels, index=all_labels.index(selected_label))
        scenario_name = next(key for key, value in SCENARIO_OPTIONS.items() if value == scenario_label)
        st.session_state.selected_scenario = scenario_name

        if scenario_name in {"custom_parallel", "custom_steepener", "custom_flattener"}:
            st.session_state.custom_scenario_magnitude = st.slider("Custom magnitude", -1.5, 1.5, float(st.session_state.custom_scenario_magnitude), 0.05)

        if _button("Apply scenario"):
            scenario = _scenario_from_selection(scenario_name)
            if scenario is None:
                st.session_state.market_state["stressed_snapshot"] = deepcopy(st.session_state.market_state["base_snapshot"])
                st.session_state.market_state["scenario"] = "none"
                st.session_state.market_state = regenerate_market_state(state)
            else:
                st.session_state.market_state = apply_state_scenario(st.session_state.market_state, scenario)
            _sync_legacy_fields()
                st.session_state.market_state = apply_state_scenario(state, scenario)
            state = st.session_state.market_state

        stress_table = make_stress_table(state["base_snapshot"], state["stressed_snapshot"])
        st.caption(f"Active stress tenors: {len(stress_table)}")

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")

        st.caption(st.session_state.market_narrative)

    st.session_state.previous_snapshot = current_snapshot


def learning_hint(text: str) -> None:
    ensure_market_state_initialized()
    if st.session_state.get("mode", "Basic") == "Learning":
    if st.session_state.mode == "Learning":
        st.info(text)
