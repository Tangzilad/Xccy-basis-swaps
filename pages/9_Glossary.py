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
        "related_pages": ["2. XCCY mechanics"],
    },
    {
        "term": "Basis Spread / Cross-Currency Basis",
        "definition": (
            "The spread (in bps) added to one leg of a cross-currency swap to compensate for "
            "supply-demand imbalances, credit differences, and balance-sheet costs. A negative "
            "basis means paying extra to obtain USD funding via swaps."
        ),
        "related_pages": ["2. XCCY mechanics", "3. Parity lab"],
    },
    {
        "term": "Basis Drag",
        "definition": (
            "The additional cost (in bps) of synthetic funding attributable to the basis spread. "
            "Measured as the difference between synthetic rates with and without basis."
        ),
        "related_pages": ["2. XCCY mechanics"],
    },
    {
        "term": "Covered Interest Parity (CIP)",
        "definition": (
            "The no-arbitrage condition linking spot FX, forward FX, and funding rates under "
            "the app quote convention (HUF per USD): "
            "F_CIP = S * (1 + r_foreign,HUF * T) / (1 + r_domestic,USD * T). "
            "In this app's parity pages, 'domestic' is the USD funding leg and 'foreign' is "
            "the HUF funding leg. Deviations of observed forwards from F_CIP are the CIP wedge/basis signal."
        ),
        "related_pages": ["3. Parity lab"],
    },
    {
        "term": "Deposit Spread vs Swap Spread",
        "definition": (
            "A deposit spread is the issuer's direct cash borrowing premium over the local risk-free/curve "
            "benchmark. A swap spread (basis spread in this lab) is the derivative premium paid/received "
            "when transforming funding across currencies. Issuance decisions compare direct funding "
            "(curve + deposit spread) versus synthetic funding (foreign curve + basis/swap spread + extra spread)."
        ),
        "related_pages": ["2. XCCY mechanics", "4. Market basis and funding transformation"],
    },
    {
        "term": "CIP Wedge / Raw Basis Wedge",
        "definition": (
            "The difference (in bps) between the rate implied by observed forwards and the "
            "actual market rate. Measures how far the market deviates from no-arbitrage parity."
        ),
        "related_pages": ["3. Parity lab"],
    },
    {
        "term": "CIP Deviation Persistence",
        "definition": (
            "The tendency for CIP wedges to remain non-zero over time because arbitrage capital is "
            "limited and frictions are real. Even when raw parity gaps are visible, balance-sheet/XVA/"
            "execution costs can keep deviations persistent instead of instantly mean-reverting."
        ),
        "related_pages": ["3. Parity lab", "5. Persistence / XVA / arbitrage limits"],
    },
    {
        "term": "Synthetic Funding",
        "definition": (
            "Raising capital in one currency and converting to another via a cross-currency swap, "
            "as an alternative to issuing directly in the target currency."
        ),
        "related_pages": ["2. XCCY mechanics", "4. Market basis and funding transformation"],
    },
    {
        "term": "Funding Transformation",
        "definition": (
            "The process of comparing direct issuance costs versus synthetic (swapped) costs "
            "to determine the cheapest funding route for each currency and tenor."
        ),
        "related_pages": ["4. Market basis and funding transformation"],
    },
    {
        "term": "Issuance Decision Inequalities (USD issuer vs HUF issuer)",
        "definition": (
            "For a HUF issuer, choose synthetic HUF funding if (USD_curve + basis + extra) < (HUF_curve + extra), "
            "equivalently domestic delta < 0. For a USD issuer, choose synthetic USD funding if "
            "(HUF_curve - basis + extra) < (USD_curve + extra), equivalently foreign delta < 0. "
            "In practice, the edge must also exceed friction/XVA bands to be actionable."
        ),
        "related_pages": [
            "4. Market basis and funding transformation",
            "7. HUF/USD strategy and stress lab",
        ],
    },
    {
        "term": "Friction / Transaction Costs",
        "definition": (
            "Real-world costs that prevent perfect arbitrage: capital charges, CVA, FVA, "
            "clearing costs, and liquidity/repo costs. These create a 'no-trade band' "
            "around fair value."
        ),
        "related_pages": ["5. Persistence / XVA / arbitrage limits"],
    },
    {
        "term": "CVA (Credit Valuation Adjustment)",
        "definition": (
            "The cost of counterparty credit risk in a derivative. Reflects the expected loss "
            "from counterparty default over the life of the trade."
        ),
        "related_pages": ["5. Persistence / XVA / arbitrage limits"],
    },
    {
        "term": "FVA (Funding Valuation Adjustment)",
        "definition": (
            "The cost of funding uncollateralised derivative positions. Reflects the spread "
            "between the risk-free rate and the institution's actual funding cost."
        ),
        "related_pages": ["5. Persistence / XVA / arbitrage limits"],
    },
    {
        "term": "XVA Bundle and Arbitrage Band (CVA/FVA/Capital)",
        "definition": (
            "The combined implementation cost of credit (CVA), funding (FVA), and capital/balance-sheet "
            "charges that widens the no-arbitrage region. A raw edge is tradable only if it exceeds this "
            "bundle-adjusted band after execution costs."
        ),
        "related_pages": ["5. Persistence / XVA / arbitrage limits", "7. HUF/USD strategy and stress lab"],
    },
    {
        "term": "Friction-Adjusted Arbitrage Band",
        "definition": (
            "The range around fair value within which no trade is profitable after all "
            "friction costs. If |raw edge| < friction band, the dislocation persists."
        ),
        "related_pages": ["5. Persistence / XVA / arbitrage limits"],
    },
    {
        "term": "Conversion Factor (CF)",
        "definition": (
            "The ratio used to translate a spread from one currency's quote space (e.g. HUF bps) "
            "into another (e.g. USD bps). Simple CF = F/S; the annuity form is "
            "CF_annuity = (sum_t DF_t * F_t / S_t) / (sum_t DF_t), i.e., a discount-factor-weighted "
            "average of forward/spot ratios across the hedge ladder."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice", "7. HUF/USD strategy and stress lab"],
    },
    {
        "term": "Hedged Pickup",
        "definition": (
            "The net return from an investment after hedging currency risk. Equals gross carry "
            "minus hedge cost, basis drag, and other frictions."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice"],
    },
    {
        "term": "Matched-Maturity Hedge",
        "definition": (
            "An FX hedge whose tenor matches the investment horizon exactly. Eliminates roll "
            "risk but may have higher upfront cost."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice"],
    },
    {
        "term": "Rolling Hedge",
        "definition": (
            "An FX hedge using shorter-dated instruments that are periodically rolled. "
            "Often cheaper in carry terms but introduces mark-to-market / roll risk."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice"],
    },
    {
        "term": "Maturity-Matched vs Rolling Hedge Trade-off",
        "definition": (
            "Matched-maturity hedges minimize path dependency and roll slippage but can lock in a less "
            "attractive initial hedge level. Rolling hedges may improve expected carry but introduce "
            "roll timing risk, mark-to-market volatility, and execution uncertainty. "
            "Choice depends on risk tolerance, horizon certainty, and expected curve dynamics."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice", "7. HUF/USD strategy and stress lab"],
    },
    {
        "term": "Risk-Adjusted Rolling Cost",
        "definition": (
            "The expected rolling hedge cost plus a penalty for roll risk, scaled by a "
            "risk-aversion parameter: RA_cost = E[roll_cost] + lambda * sigma_roll."
        ),
        "related_pages": ["6. Hedged pickup and hedge choice"],
    },
    {
        "term": "Stress Scenario",
        "definition": (
            "A set of simultaneous shocks to rates, FX, basis, and credit/friction assumptions "
            "designed to test strategy robustness under adverse conditions."
        ),
        "related_pages": ["7. HUF/USD strategy and stress lab", "8. Consolidated dashboard"],
    },
    {
        "term": "Actionability",
        "definition": (
            "Whether a trade clears the friction-adjusted no-trade band and can be executed "
            "profitably. A strategy may have positive edge in theory but not be actionable "
            "if frictions exceed the edge."
        ),
        "related_pages": [
            "5. Persistence / XVA / arbitrage limits",
            "7. HUF/USD strategy and stress lab",
            "8. Consolidated dashboard",
        ],
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
