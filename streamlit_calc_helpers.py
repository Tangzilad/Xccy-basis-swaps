"""Shared Streamlit helpers for collapsible calculation windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import streamlit as st


@dataclass(slots=True)
class CalculationWindow:
    """Container for calculation details displayed in the UI."""

    title: str
    formula: str
    substituted_values: str
    sign_convention_notes: Sequence[str] = field(default_factory=tuple)
    assumptions: Sequence[str] = field(default_factory=tuple)
    result: str = ""
    expanded: bool = False
    quote_convention: str = ""
    perspective: str = ""
    positive_interpretation: str = ""
    negative_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class SignConventionContext:
    """Shared sign-convention details applied to a page's calculation windows."""

    quote_convention: str
    perspective: str
    positive_interpretation: str
    negative_interpretation: str


DEFAULT_CALCULATION_TITLES: tuple[str, ...] = (
    "Theoretical forward",
    "Implied HUF rate",
    "Implied USD rate",
    "Raw basis wedge",
    "Synthetic funding cost",
    "Friction-adjusted arbitrage band",
    "Hedged pickup",
    "Conversion factor",
    "Stressed vs base deltas",
)


_CALCULATION_KEYS: tuple[str, ...] = (
    "theoretical_forward",
    "implied_huf_rate",
    "implied_usd_rate",
    "raw_basis_wedge",
    "synthetic_funding_cost",
    "friction_adjusted_arbitrage_band",
    "hedged_pickup",
    "conversion_factor",
    "stressed_vs_base_deltas",
)


CALCULATION_KEY_TO_TITLE = dict(zip(_CALCULATION_KEYS, DEFAULT_CALCULATION_TITLES))


def render_calculation_window(window: CalculationWindow) -> None:
    """Render a single collapsible window containing a calculation breakdown."""
    with st.expander(window.title, expanded=window.expanded):
        st.markdown("**Formula**")
        st.latex(window.formula)

        st.markdown("**Substituted values**")
        st.markdown(window.substituted_values)

        st.markdown("**Sign convention notes**")
        if window.sign_convention_notes:
            for note in window.sign_convention_notes:
                st.markdown(f"- {note}")
        else:
            st.markdown("- None provided")

        st.markdown("**Assumptions**")
        if window.assumptions:
            for assumption in window.assumptions:
                st.markdown(f"- {assumption}")
        else:
            st.markdown("- None provided")

        st.markdown("**Result**")
        st.success(window.result)

        st.markdown("**Quote convention and sign interpretation**")
        st.markdown(f"- Quote convention: {window.quote_convention or 'Not specified'}")
        st.markdown(f"- Perspective: {window.perspective or 'Not specified'}")
        st.markdown(f"- Positive result: {window.positive_interpretation or 'Not specified'}")
        st.markdown(f"- Negative result: {window.negative_interpretation or 'Not specified'}")


def render_shared_sign_convention(context: SignConventionContext) -> None:
    """Render a shared sign-convention panel for a page."""
    st.info(
        "\n".join(
            [
                "**Shared sign convention (applies to all calculation windows below)**",
                f"- Quote convention: {context.quote_convention}",
                f"- Perspective: {context.perspective}",
                f"- Positive result: {context.positive_interpretation}",
                f"- Negative result: {context.negative_interpretation}",
            ]
        )
    )


def _apply_sign_context(window: CalculationWindow, context: SignConventionContext | None) -> CalculationWindow:
    if context is None:
        return window
    return CalculationWindow(
        title=window.title,
        formula=window.formula,
        substituted_values=window.substituted_values,
        sign_convention_notes=tuple(window.sign_convention_notes),
        assumptions=tuple(window.assumptions),
        result=window.result,
        expanded=window.expanded,
        quote_convention=window.quote_convention or context.quote_convention,
        perspective=window.perspective or context.perspective,
        positive_interpretation=window.positive_interpretation or context.positive_interpretation,
        negative_interpretation=window.negative_interpretation or context.negative_interpretation,
    )


def render_calculation_windows(
    windows: Iterable[CalculationWindow],
    *,
    sign_convention: SignConventionContext | None = None,
) -> None:
    """Render a list of collapsible calculation windows."""
    for window in windows:
        render_calculation_window(_apply_sign_context(window, sign_convention))


def render_required_calculation_windows(
    calculations: dict[str, CalculationWindow],
    *,
    default_expanded: bool = False,
    sign_convention: SignConventionContext | None = None,
) -> None:
    """Render all required windows in a consistent order.

    Parameters
    ----------
    calculations:
        Mapping keyed by the expected identifiers (e.g. ``theoretical_forward``).
    default_expanded:
        Fallback expanded value when a provided window does not explicitly set one.
    """
    windows: list[CalculationWindow] = []
    for key in _CALCULATION_KEYS:
        if key not in calculations:
            raise KeyError(
                f"Missing required calculation window: '{key}'. "
                "Provide all required calculation entries."
            )
        window = calculations[key]
        if not isinstance(window, CalculationWindow):
            raise TypeError(
                f"Expected CalculationWindow for key '{key}', got {type(window)!r}."
            )
        if window.expanded != default_expanded:
            windows.append(window)
        else:
            windows.append(
                CalculationWindow(
                    title=window.title,
                    formula=window.formula,
                    substituted_values=window.substituted_values,
                    sign_convention_notes=tuple(window.sign_convention_notes),
                    assumptions=tuple(window.assumptions),
                    result=window.result,
                    expanded=default_expanded,
                )
            )

    render_calculation_windows(windows, sign_convention=sign_convention)
