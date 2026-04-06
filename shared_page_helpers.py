"""Shared helpers used across Streamlit page modules.

Centralises the market-state extraction logic that was previously duplicated
in every page file, and provides reusable pedagogical UI components.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import streamlit as st

from src.state.session_access import get_canonical_market_context


# ---------------------------------------------------------------------------
# Market state extraction
# ---------------------------------------------------------------------------

def get_market_params(session_state: dict) -> dict:
    """Extract core market parameters from session state.

    Returns a dict with keys: spot_fx, usd_rate, huf_rate, basis_bps.
    All rates are decimals (e.g. 0.0425), basis is in bps (e.g. -22.0).
    """
    ms = session_state.get("market_state")
    if isinstance(ms, dict) and "base_snapshot" in ms:
        summary = get_canonical_market_context(session_state)["summary_1y"]["base"]
        return {
            "spot_fx": float(summary["spot_fx"]),
            "usd_rate": float(summary["usd_rate"]),
            "huf_rate": float(summary["huf_rate"]),
            "basis_bps": float(summary["basis_bps"]),
        }
    if isinstance(ms, dict):
        return ms
    if ms is not None:
        return {
            "spot_fx": float(getattr(ms, "spot_fx", session_state.get("spot_fx", 365.0))),
            "usd_rate": float(ms.huf_usd_curves["usd"].iloc[0]["usd_zero_rate"]),
            "huf_rate": float(ms.huf_usd_curves["huf"].iloc[0]["huf_zero_rate"]),
            "basis_bps": float(ms.basis_curve.iloc[0]["basis_bps"]),
        }
    fallback = {
        "spot_fx": float(session_state.get("spot_fx", 365.0)),
        "usd_rate": float(session_state.get("base_rate", 4.25)) / 100.0,
        "huf_rate": float(session_state.get("quote_rate", 5.0)) / 100.0,
        "basis_bps": float(session_state.get("cross_currency_basis_bps", -22.0)),
    }
    session_state["market_state"] = fallback
    return fallback


def get_funding_params(session_state: dict) -> dict:
    """Like get_market_params but includes extra_spread_bps for funding pages."""
    params = get_market_params(session_state)
    params.setdefault("extra_spread_bps", 12.0)
    return params


def as_decimal(v: float) -> float:
    """Convert percentage to decimal if needed (e.g. 4.25 -> 0.0425)."""
    return v / 100.0 if v > 1 else v


def from_decimal(v: float) -> float:
    """Convert decimal to percentage if needed (e.g. 0.0425 -> 4.25)."""
    return v * 100.0 if v < 1 else v


# ---------------------------------------------------------------------------
# Pedagogical UI components
# ---------------------------------------------------------------------------

LEARNING_OBJECTIVES: Dict[int, Dict[str, Any]] = {
    1: {
        "title": "XCCY Mechanics",
        "objectives": [
            "Understand how cross-currency swap cashflows are structured",
            "Calculate synthetic funding costs with and without basis",
            "Interpret basis drag and its impact on funding economics",
        ],
        "prerequisites": [],
    },
    2: {
        "title": "Parity Lab",
        "objectives": [
            "Apply covered interest parity (CIP) to derive fair forward rates",
            "Decompose the gap between observed and CIP-implied forwards",
            "Measure raw basis wedges across a tenor ladder",
        ],
        "prerequisites": ["XCCY Mechanics"],
    },
    3: {
        "title": "Market Basis & Funding Transformation",
        "objectives": [
            "Compare direct vs. synthetic funding routes across tenors",
            "Identify when issuing in a foreign currency + swapping is cheaper",
            "Interpret funding gaps from the perspective of issuers, investors, and treasurers",
        ],
        "prerequisites": ["XCCY Mechanics", "Parity Lab"],
    },
    4: {
        "title": "Persistence / XVA / Arbitrage Limits",
        "objectives": [
            "Enumerate friction components (capital, CVA, FVA, clearing, liquidity)",
            "Calculate friction-adjusted arbitrage bands",
            "Explain why basis dislocations persist despite apparent mispricing",
        ],
        "prerequisites": ["Parity Lab"],
    },
    5: {
        "title": "Hedged Pickup & Hedge Choice",
        "objectives": [
            "Compute conversion factors (simple and curve-aware) for spread translation",
            "Decompose hedged pickup into gross carry, hedge cost, basis drag, and frictions",
            "Compare matched-maturity vs. rolling hedge economics with risk adjustment",
        ],
        "prerequisites": ["XCCY Mechanics", "Persistence / XVA"],
    },
    6: {
        "title": "HUF/USD Strategy & Stress Lab",
        "objectives": [
            "Integrate all prior concepts into a coherent strategy assessment",
            "Compare base vs. stressed metrics to evaluate strategy robustness",
            "Determine whether hedged pickup survives widened friction bands under stress",
        ],
        "prerequisites": ["All prior lessons"],
    },
}


KEY_TAKEAWAYS: Dict[int, List[str]] = {
    1: [
        "The basis spread directly affects the synthetic cost of cross-currency funding.",
        "Basis drag measures how much worse (or better) synthetic funding is versus the no-basis benchmark.",
        "Swap cashflows have clear directionality: always specify which leg you receive.",
    ],
    2: [
        "CIP provides the theoretical no-arbitrage forward; deviations reveal basis pressure.",
        "A positive raw wedge (HUF/USD convention) means synthetic USD borrowing via HUF is more expensive.",
        "Basis wedges tend to widen at longer tenors and under stress regimes.",
    ],
    3: [
        "The cheapest funding route depends on the sign and magnitude of the basis spread.",
        "Direct and synthetic routes can flip advantage at different tenors.",
        "Funding transformation decisions must account for operational and liquidity constraints beyond pure economics.",
    ],
    4: [
        "Friction costs create a no-trade band around the theoretical fair value.",
        "Even large basis wedges may not be actionable if frictions exceed the edge.",
        "Capacity and counterparty quality multipliers can materially shift the friction band.",
    ],
    5: [
        "The conversion factor translates spreads from one quote space to another; it is not simply the FX rate.",
        "Hedged pickup is always less than the nominal yield differential after subtracting costs.",
        "Rolling hedges introduce mark-to-market risk that must be priced via risk aversion parameters.",
    ],
    6: [
        "Stress scenarios can simultaneously widen basis, increase frictions, and erode pickup.",
        "A strategy that works in calm markets may become unactionable under stress.",
        "Robust strategies maintain positive net pickup even after friction-band widening.",
    ],
}


COMPREHENSION_CHECKS: Dict[int, List[Dict[str, str]]] = {
    1: [
        {
            "question": "If the cross-currency basis becomes more negative, does synthetic USD funding become cheaper or more expensive?",
            "answer": "More expensive. A more negative basis increases the cost added to the HUF leg, raising the synthetic USD rate.",
        },
        {
            "question": "Why does the sign convention matter when interpreting swap cashflows?",
            "answer": "Because the same swap has opposite signs for the two counterparties. Specifying 'USD receiver / HUF payer' removes ambiguity.",
        },
    ],
    2: [
        {
            "question": "If the observed forward equals the CIP-implied forward exactly, what is the raw basis wedge?",
            "answer": "Zero. The market embeds no deviation from covered interest parity.",
        },
        {
            "question": "What economic forces can cause the CIP wedge to persist?",
            "answer": "Balance-sheet constraints (capital rules, leverage ratios), hedging demand imbalances, and counterparty credit limits prevent pure arbitrage from closing the gap.",
        },
    ],
    3: [
        {
            "question": "When is it cheaper to issue in a foreign currency and swap into domestic funding?",
            "answer": "When the synthetic domestic rate (foreign rate + basis + extras) is lower than the direct domestic rate. This typically occurs when the basis is sufficiently negative.",
        },
    ],
    4: [
        {
            "question": "If total frictions are 29 bps and the raw basis edge is 22 bps, is the trade actionable?",
            "answer": "No. The raw edge (22 bps) is less than the friction band (29 bps), so the trade does not clear the no-trade zone.",
        },
    ],
    5: [
        {
            "question": "Why can a higher nominal yield differential still produce negative net hedged pickup?",
            "answer": "Because hedge implementation costs, basis drag, and frictions are subtracted from the gross carry. If these exceed the nominal differential, net pickup turns negative.",
        },
    ],
    6: [
        {
            "question": "What three metrics should you check to determine if a strategy survives a stress scenario?",
            "answer": "1) Whether the net pickup remains positive, 2) Whether the raw edge exceeds the (now wider) friction band, 3) Whether the basis move invalidates your hedge economics.",
        },
    ],
}


def render_learning_objectives(step_index: int) -> None:
    """Display learning objectives for the current lesson."""
    info = LEARNING_OBJECTIVES.get(step_index)
    if info is None:
        return
    with st.expander("Learning objectives", expanded=True):
        for obj in info["objectives"]:
            st.markdown(f"- {obj}")
        if info["prerequisites"]:
            st.caption(f"Prerequisites: {', '.join(info['prerequisites'])}")


def render_key_takeaways(step_index: int) -> None:
    """Display key takeaways at the bottom of a lesson page."""
    takeaways = KEY_TAKEAWAYS.get(step_index)
    if takeaways is None:
        return
    st.markdown("---")
    st.markdown("### Key Takeaways")
    for t in takeaways:
        st.success(t)


def render_comprehension_checks(step_index: int) -> None:
    """Display self-assessment questions for the lesson."""
    checks = COMPREHENSION_CHECKS.get(step_index)
    if checks is None:
        return
    st.markdown("### Check Your Understanding")
    for i, check in enumerate(checks):
        with st.expander(f"Q{i+1}: {check['question']}"):
            st.info(check["answer"])


def render_page_header(
    step_index: int,
    title: str,
    *,
    show_objectives: bool = True,
) -> None:
    """Unified page header: title + learning objectives."""
    st.title(title)
    if show_objectives and st.session_state.get("mode") == "Learning":
        render_learning_objectives(step_index)


def render_page_footer(step_index: int) -> None:
    """Unified page footer: key takeaways + comprehension checks."""
    if st.session_state.get("mode") == "Learning":
        render_key_takeaways(step_index)
        render_comprehension_checks(step_index)
