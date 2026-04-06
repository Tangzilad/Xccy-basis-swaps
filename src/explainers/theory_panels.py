"""Reusable theory panel text and formula rendering helpers.

Import this module from page-level views to avoid hardcoded, page-local theory
copy and equation strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence


@dataclass(frozen=True)
class TheoryPanel:
    """Standardized content block for economic intuition sections."""

    title: str
    intuition: str
    formula: str
    variables: Mapping[str, str]


@dataclass(frozen=True)
class PedagogicalScaffold:
    """Reusable top-of-page pedagogical scaffold text."""

    teaches: str
    why_it_matters_huf_usd: str
    how_to_read_surface: str
    how_to_read_deep: str


def render_formula_latex(lhs: str, rhs: str) -> str:
    """Render a display-style LaTeX equation string."""

    return f"$$ {lhs} = {rhs} $$"


def render_formula_plain(lhs: str, rhs: str) -> str:
    """Render a plain-text equation string for markdown/table contexts."""

    return f"{lhs} = {rhs}"


THEORY_PANELS: Dict[str, TheoryPanel] = {
    "basis_spread": TheoryPanel(
        title="Cross-currency basis spread",
        intuition=(
            "The basis captures the premium/discount required to swap floating "
            "funding across currencies after hedging FX risk."
        ),
        formula=render_formula_latex("b_{t,T}", "S_{ccy}(t,T) - S_{OIS}(t,T)"),
        variables={
            "b_{t,T}": "Cross-currency basis for tenor T",
            "S_{ccy}(t,T)": "Quoted all-in swap spread in funding currency",
            "S_{OIS}(t,T)": "Risk-free OIS-implied spread",
        },
    ),
    "covered_interest_parity": TheoryPanel(
        title="Covered interest parity (CIP) wedge",
        intuition=(
            "When CIP holds exactly, forward FX embeds rate differentials. "
            "Persistent deviations imply balance-sheet constraints or hedging demand imbalance."
        ),
        formula=render_formula_latex(
            "w_{cip}",
            "\frac{F_t}{S_t} - \frac{1 + r_d\tau}{1 + r_f\tau}",
        ),
        variables={
            "w_{cip}": "CIP wedge",
            "F_t": "FX forward rate",
            "S_t": "FX spot rate",
            "r_d, r_f": "Domestic and foreign funding rates",
            "\\tau": "Year fraction for tenor",
        },
    ),
    "hedged_return": TheoryPanel(
        title="Hedged investor return",
        intuition=(
            "For foreign investors, asset carry and hedge carry jointly determine "
            "the fully hedged return after basis costs."
        ),
        formula=render_formula_latex("R^{hedged}", "R^{asset} + carry_{FX} - b"),
        variables={
            "R^{hedged}": "Investor return after currency hedge",
            "R^{asset}": "Local-currency asset return",
            "carry_{FX}": "Forward/spot roll-down from hedge",
            "b": "Basis paid/received in hedge structure",
        },
    ),
}

PEDAGOGICAL_SCAFFOLDS: Dict[int, PedagogicalScaffold] = {
    2: PedagogicalScaffold(
        teaches="How HUF/USD cross-currency swaps turn cashflows and forwards into synthetic funding.",
        why_it_matters_huf_usd="Hungarian borrowers and investors often compare direct USD funding versus HUF funding swapped back to USD.",
        how_to_read_surface="Use the metrics/table to check sign and scale of basis drag quickly.",
        how_to_read_deep="Use derivation expanders to trace each cashflow and synthetic-rate formula.",
    ),
    3: PedagogicalScaffold(
        teaches="How to decompose observed HUF/USD forwards into CIP-implied values and a raw wedge.",
        why_it_matters_huf_usd="Persistent HUF/USD wedge drives real funding differentials for local issuers and foreign investors.",
        how_to_read_surface="Start with CIP-implied forward, implied rates, and raw wedge sign.",
        how_to_read_deep="Open derivations to inspect the implied-rate algebra and tenor scaling.",
    ),
    4: PedagogicalScaffold(
        teaches="How market basis transforms all-in funding costs across direct and synthetic issuance routes.",
        why_it_matters_huf_usd="A few bps in HUF/USD basis can flip whether Hungarian or USD issuance is economically better.",
        how_to_read_surface="Read the 1Y deltas and recommendation panel first.",
        how_to_read_deep="Use derivations to reconstruct domestic, synthetic, and delta terms.",
    ),
    5: PedagogicalScaffold(
        teaches="Why CIP dislocations can persist once XVA, balance-sheet, and execution frictions are included.",
        why_it_matters_huf_usd="Even clear HUF/USD wedge signals may be untradeable after capital and funding constraints.",
        how_to_read_surface="Compare raw edge vs total friction and check actionability.",
        how_to_read_deep="Open derivations to inspect each friction component and capacity multiplier.",
    ),
    6: PedagogicalScaffold(
        teaches="How conversion factors and hedge implementation choices determine realized hedged pickup.",
        why_it_matters_huf_usd="HUF carry can look attractive but net USD pickup depends on hedge cost, basis drag, and roll risk.",
        how_to_read_surface="Use net pickup and preferred hedge outputs as the decision snapshot.",
        how_to_read_deep="Use derivations to audit conversion-factor weighting and risk-adjusted rolling economics.",
    ),
    7: PedagogicalScaffold(
        teaches="How to combine parity, funding, frictions, conversion, and hedging into a scenario decision process.",
        why_it_matters_huf_usd="HUF/USD strategy can change abruptly under stress; this page shows which channel drives the shift.",
        how_to_read_surface="Focus on stressed-vs-base deltas and whether preferred hedge flips.",
        how_to_read_deep="Use derivations to attribute changes to wedge, friction band, and hedge terms.",
    ),
}


def get_theory_panel(panel_key: str, fallback_key: Optional[str] = None) -> TheoryPanel:
    """Lookup a theory panel by key.

    Args:
        panel_key: Primary panel identifier.
        fallback_key: Optional fallback key if primary key is missing.
    """

    panel = THEORY_PANELS.get(panel_key)
    if panel is not None:
        return panel

    if fallback_key is not None and fallback_key in THEORY_PANELS:
        return THEORY_PANELS[fallback_key]

    available = ", ".join(sorted(THEORY_PANELS.keys()))
    raise KeyError(f"Unknown panel '{panel_key}'. Available: {available}")


def panel_to_dict(panel_key: str, fallback_key: Optional[str] = None) -> Dict[str, object]:
    """Serialize theory panel content for JSON/page state payloads."""

    panel = get_theory_panel(panel_key=panel_key, fallback_key=fallback_key)
    return {
        "title": panel.title,
        "intuition": panel.intuition,
        "formula": panel.formula,
        "variables": dict(panel.variables),
    }


def render_pedagogical_scaffold(
    st: object,
    *,
    page_number: int,
    learning_path: Sequence[str],
    quantitative_outputs: Sequence[str],
    derivation_items: Sequence[tuple[str, str]],
) -> None:
    """Render shared top-of-page teaching sections in a fixed order."""

    scaffold = PEDAGOGICAL_SCAFFOLDS[page_number]

    st.subheader("What this page teaches")
    st.write(scaffold.teaches)

    st.subheader("Why it matters economically (HUF/USD-specific)")
    st.write(scaffold.why_it_matters_huf_usd)

    st.subheader("How to read this page (surface vs deep)")
    st.markdown(f"- **Surface:** {scaffold.how_to_read_surface}")
    st.markdown(f"- **Deep:** {scaffold.how_to_read_deep}")

    st.subheader("Quantitative outputs")
    for item in quantitative_outputs:
        st.markdown(f"- {item}")

    prev_page = learning_path[page_number - 2] if page_number > 1 else "Start"
    next_page = learning_path[page_number] if page_number < len(learning_path) else "End"
    st.caption(f"Connects from previous page: **{prev_page}**")
    st.caption(f"Leads to next page: **{next_page}**")

    st.subheader("Derivation expanders")
    for title, body in derivation_items:
        with st.expander(title, expanded=False):
            st.write(body)
