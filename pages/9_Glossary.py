"""Glossary -- key terms and concepts used throughout the learning lab."""

from __future__ import annotations

import streamlit as st

from ui_shell import ensure_market_state_initialized, render_global_shell


GLOSSARY = [
    {
        "term": "Cross-Currency Basis Swap (XCCY)",
        "definition": (
            "A derivative where two counterparties exchange floating-rate payments in different "
            "currencies, plus principal at inception and maturity. The 'basis' is the spread "
            "added to one leg to make the swap fair."
        ),
        "related_pages": ["2. XCCY Mechanics"],
    },
    {
        "term": "Basis Spread / Cross-Currency Basis",
        "definition": (
            "The spread (in bps) added to one leg of a cross-currency swap to compensate for "
            "supply-demand imbalances, credit differences, and balance-sheet costs. A negative "
            "basis means paying extra to obtain USD funding via swaps."
        ),
        "related_pages": ["2. XCCY Mechanics", "3. Parity Lab"],
    },
    {
        "term": "Basis Drag",
        "definition": (
            "The additional cost (in bps) of synthetic funding attributable to the basis spread. "
            "Measured as the difference between synthetic rates with and without basis."
        ),
        "related_pages": ["2. XCCY Mechanics"],
    },
    {
        "term": "Covered Interest Parity (CIP)",
        "definition": (
            "The no-arbitrage condition linking spot FX, forward FX, and interest rates: "
            "F = S * (1 + r_d * T) / (1 + r_f * T). Deviations from CIP reveal the basis."
        ),
        "related_pages": ["3. Parity Lab"],
    },
    {
        "term": "CIP Wedge / Raw Basis Wedge",
        "definition": (
            "The difference (in bps) between the rate implied by observed forwards and the "
            "actual market rate. Measures how far the market deviates from no-arbitrage parity."
        ),
        "related_pages": ["3. Parity Lab"],
    },
    {
        "term": "Synthetic Funding",
        "definition": (
            "Raising capital in one currency and converting to another via a cross-currency swap, "
            "as an alternative to issuing directly in the target currency."
        ),
        "related_pages": ["2. XCCY Mechanics", "4. Funding Transformation"],
    },
    {
        "term": "Funding Transformation",
        "definition": (
            "The process of comparing direct issuance costs versus synthetic (swapped) costs "
            "to determine the cheapest funding route for each currency and tenor."
        ),
        "related_pages": ["4. Funding Transformation"],
    },
    {
        "term": "Friction / Transaction Costs",
        "definition": (
            "Real-world costs that prevent perfect arbitrage: capital charges, CVA, FVA, "
            "clearing costs, and liquidity/repo costs. These create a 'no-trade band' "
            "around fair value."
        ),
        "related_pages": ["5. Persistence / XVA"],
    },
    {
        "term": "CVA (Credit Valuation Adjustment)",
        "definition": (
            "The cost of counterparty credit risk in a derivative. Reflects the expected loss "
            "from counterparty default over the life of the trade."
        ),
        "related_pages": ["5. Persistence / XVA"],
    },
    {
        "term": "FVA (Funding Valuation Adjustment)",
        "definition": (
            "The cost of funding uncollateralised derivative positions. Reflects the spread "
            "between the risk-free rate and the institution's actual funding cost."
        ),
        "related_pages": ["5. Persistence / XVA"],
    },
    {
        "term": "Friction-Adjusted Arbitrage Band",
        "definition": (
            "The range around fair value within which no trade is profitable after all "
            "friction costs. If |raw edge| < friction band, the dislocation persists."
        ),
        "related_pages": ["5. Persistence / XVA"],
    },
    {
        "term": "Conversion Factor (CF)",
        "definition": (
            "The ratio used to translate a spread from one currency's quote space (e.g. HUF bps) "
            "into another (e.g. USD bps). Simple CF = F/S; curve-aware CF uses annuity-weighted "
            "forward/spot ratios across tenors."
        ),
        "related_pages": ["6. Hedged Pickup"],
    },
    {
        "term": "Hedged Pickup",
        "definition": (
            "The net return from an investment after hedging currency risk. Equals gross carry "
            "minus hedge cost, basis drag, and other frictions."
        ),
        "related_pages": ["6. Hedged Pickup"],
    },
    {
        "term": "Matched-Maturity Hedge",
        "definition": (
            "An FX hedge whose tenor matches the investment horizon exactly. Eliminates roll "
            "risk but may have higher upfront cost."
        ),
        "related_pages": ["6. Hedged Pickup"],
    },
    {
        "term": "Rolling Hedge",
        "definition": (
            "An FX hedge using shorter-dated instruments that are periodically rolled. "
            "Often cheaper in carry terms but introduces mark-to-market / roll risk."
        ),
        "related_pages": ["6. Hedged Pickup"],
    },
    {
        "term": "Risk-Adjusted Rolling Cost",
        "definition": (
            "The expected rolling hedge cost plus a penalty for roll risk, scaled by a "
            "risk-aversion parameter: RA_cost = E[roll_cost] + lambda * sigma_roll."
        ),
        "related_pages": ["6. Hedged Pickup"],
    },
    {
        "term": "Stress Scenario",
        "definition": (
            "A set of simultaneous shocks to rates, FX, basis, and credit/friction assumptions "
            "designed to test strategy robustness under adverse conditions."
        ),
        "related_pages": ["7. Strategy & Stress Lab"],
    },
    {
        "term": "Actionability",
        "definition": (
            "Whether a trade clears the friction-adjusted no-trade band and can be executed "
            "profitably. A strategy may have positive edge in theory but not be actionable "
            "if frictions exceed the edge."
        ),
        "related_pages": ["5. Persistence / XVA", "7. Strategy & Stress Lab"],
    },
]


def render_page() -> None:
    st.set_page_config(page_title="Glossary", page_icon="📖", layout="wide")
    ensure_market_state_initialized()
    render_global_shell()
    st.session_state.suggested_page = "9. Glossary"

    st.title("Glossary")
    st.caption("Key terms and concepts used throughout the XCCY Basis Learning Lab.")

    # Search filter
    search = st.text_input("Filter terms", placeholder="Type to search...")

    filtered = GLOSSARY
    if search.strip():
        query = search.strip().lower()
        filtered = [
            g for g in GLOSSARY
            if query in g["term"].lower() or query in g["definition"].lower()
        ]

    if not filtered:
        st.info("No matching terms found.")

    for entry in filtered:
        with st.expander(entry["term"]):
            st.markdown(entry["definition"])
            if entry["related_pages"]:
                st.caption(f"Related: {', '.join(entry['related_pages'])}")


if __name__ == "__main__":
    render_page()
else:
    render_page()
