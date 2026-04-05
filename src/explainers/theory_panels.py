"""Reusable theory panel text and formula rendering helpers.

Import this module from page-level views to avoid hardcoded, page-local theory
copy and equation strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class TheoryPanel:
    """Standardized content block for economic intuition sections."""

    title: str
    intuition: str
    formula: str
    variables: Mapping[str, str]


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
