from __future__ import annotations

from copy import deepcopy

import streamlit as st

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

ROLE_OPTIONS = ["issuer", "investor", "treasury", "arbitrageur"]

EXPLANATION_INCLUDE_KEYS = {
    "mechanics": ["spot_fx", "base_rate", "quote_rate", "cross_currency_basis_bps", "vol_regime"],
    "parity": ["base_rate", "quote_rate", "spot_fx", "cross_currency_basis_bps", "vol_regime"],
    "funding": ["cross_currency_basis_bps", "base_rate", "quote_rate", "vol_regime"],
    "frictions": ["cross_currency_basis_bps", "vol_regime", "base_rate", "quote_rate"],
    "hedge": ["cross_currency_basis_bps", "spot_fx", "vol_regime", "quote_rate", "base_rate"],
    "stress": ["vol_regime", "cross_currency_basis_bps", "spot_fx", "base_rate", "quote_rate"],
    "overview": ["base_rate", "quote_rate", "spot_fx", "cross_currency_basis_bps", "vol_regime"],
}


def _init_defaults() -> None:
    defaults = {
        "mode": "Basic",
        "base_rate": 4.25,
        "quote_rate": 5.0,
        "spot_fx": 1.08,
        "cross_currency_basis_bps": -22,
        "vol_regime": "Normal",
        "suggested_page": LEARNING_PATH[0],
        "active_role": "treasury",
        "latest_transition_narrative": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


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
    _init_defaults()
    previous_snapshot = deepcopy(_capture_snapshot())

    with st.sidebar:
        st.header("Learning + Market Controls")
        st.session_state.mode = st.segmented_control(
            "Mode",
            options=["Basic", "Learning"],
            default=st.session_state.mode,
            help="Basic simplifies narrative. Learning adds rationale and extra interpretation.",
        )

        st.subheader("Global market-state controls")
        st.session_state.base_rate = st.slider(
            "Base currency policy rate (%)", 0.0, 12.0, float(st.session_state.base_rate), 0.05
        )
        st.session_state.quote_rate = st.slider(
            "Quote currency policy rate (%)", 0.0, 15.0, float(st.session_state.quote_rate), 0.05
        )
        st.session_state.spot_fx = st.number_input(
            "Spot FX", min_value=0.1000, max_value=50.0, value=float(st.session_state.spot_fx), step=0.0001
        )
        st.session_state.cross_currency_basis_bps = st.slider(
            "Cross-currency basis (bps)", -250, 250, int(st.session_state.cross_currency_basis_bps), 1
        )
        st.session_state.vol_regime = st.selectbox(
            "Volatility regime", ["Calm", "Normal", "Stressed"],
            index=["Calm", "Normal", "Stressed"].index(st.session_state.vol_regime),
        )
        st.session_state.active_role = st.selectbox(
            "Interpretation role",
            options=ROLE_OPTIONS,
            index=ROLE_OPTIONS.index(st.session_state.active_role),
            help="Narrative interpretation will adapt to this desk perspective.",
        )

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
                st.write(
                    f"• {change['name']}: {change['previous']} → {change['current']}"
                )
        else:
            st.write("• No included inputs changed in this transition.")
        st.caption(f"Transmission: {transition_payload['transmission_mechanism']}")
        st.caption(f"Economic channel: {transition_payload['economic_channel']}")
        st.caption(
            f"Role ({st.session_state.active_role}): {transition_payload['role_interpretation']}"
        )
        st.caption(f"Inspect next: {transition_payload['inspect_next']}")

        st.divider()
        st.subheader("Suggested learning path")
        for step in LEARNING_PATH:
            marker = "✅" if st.session_state.get("suggested_page") == step else "•"
            st.write(f"{marker} {step}")


def learning_hint(text: str) -> None:
    if st.session_state.get("mode", "Basic") == "Learning":
        st.info(text)
