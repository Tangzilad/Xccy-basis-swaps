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


CALCULATION_KEY_TO_TITLE: dict[str, str] = {
    "theoretical_forward": "Theoretical forward",
    "implied_huf_rate": "Implied HUF rate",
    "implied_usd_rate": "Implied USD rate",
    "forward_difference": "Forward difference",
    "relative_forward_difference": "Relative forward difference",
    "raw_basis_wedge": "Raw basis wedge",
    "synthetic_funding_cost": "Synthetic funding cost",
    "friction_adjusted_arbitrage_band": "Friction-adjusted arbitrage band",
    "hedged_pickup": "Hedged pickup",
    "conversion_factor": "Conversion factor",
    "stressed_vs_base_deltas": "Stressed vs base deltas",
}


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


def render_calculation_windows(windows: Iterable[CalculationWindow]) -> None:
    """Render a list of collapsible calculation windows."""
    for window in windows:
        render_calculation_window(window)


def validate_required_calculation_windows(
    calculations: dict[str, CalculationWindow],
    *,
    required_keys: Sequence[str],
    page_name: str | None = None,
    default_expanded: bool = False,
) -> list[CalculationWindow]:
    """Validate and normalize required windows for an active page."""
    missing_keys = [key for key in required_keys if key not in calculations]
    if missing_keys:
        expected_titles = [
            f"{key} ({CALCULATION_KEY_TO_TITLE.get(key, key)})"
            for key in missing_keys
        ]
        page_descriptor = f" for page '{page_name}'" if page_name else ""
        raise KeyError(
            "Missing required calculation window(s)"
            f"{page_descriptor}: {', '.join(expected_titles)}. "
            f"Provided keys: {sorted(calculations)}."
        )

    windows: list[CalculationWindow] = []
    for key in required_keys:
        window = calculations[key]
        if not isinstance(window, CalculationWindow):
            raise TypeError(
                f"Expected CalculationWindow for key '{key}', got {type(window)!r}."
            )
        if window.expanded != default_expanded:
            windows.append(window)
            continue
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
    return windows


def render_required_calculation_windows(
    calculations: dict[str, CalculationWindow],
    *,
    required_keys: Sequence[str],
    page_name: str | None = None,
    default_expanded: bool = False,
) -> None:
    """Render required windows in a consistent order for the active page.

    Parameters
    ----------
    calculations:
        Mapping keyed by the expected identifiers (e.g. ``theoretical_forward``).
    default_expanded:
        Fallback expanded value when a provided window does not explicitly set one.
    """
    windows = validate_required_calculation_windows(
        calculations,
        required_keys=required_keys,
        page_name=page_name,
        default_expanded=default_expanded,
    )
    render_calculation_windows(windows)
