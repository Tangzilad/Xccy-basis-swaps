"""Shared Streamlit helpers for collapsible calculation windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

@dataclass(slots=True)
class CalculationWindow:
    """Pedagogical container for calculation details displayed in the UI."""

    title: str
    concept_meaning: str
    why_it_matters: str
    formula: str
    methodology_rationale: str
    inputs_used: str
    substituted_values: str
    derivation_steps: Sequence[str] = field(default_factory=tuple)
    deep_derivation: Sequence[str] = field(default_factory=tuple)
    assumptions: Sequence[str] = field(default_factory=tuple)
    interpretation: str = ""
    common_misunderstandings: Sequence[str] = field(default_factory=tuple)
    result: str = ""
    expanded: bool = False

    def validate(self, *, required_fields: Sequence[str] | None = None) -> None:
        """Validate required narrative sections are populated."""
        required = tuple(
            required_fields
            or (
                "concept_meaning",
                "why_it_matters",
                "formula",
                "methodology_rationale",
                "inputs_used",
                "substituted_values",
                "derivation_steps",
                "assumptions",
                "interpretation",
                "common_misunderstandings",
                "result",
            )
        )

        missing: list[str] = []
        for field_name in required:
            value = getattr(self, field_name)
            if isinstance(value, str):
                if not value.strip():
                    missing.append(field_name)
            elif isinstance(value, Sequence):
                if len(value) == 0 or all(not str(item).strip() for item in value):
                    missing.append(field_name)
            else:
                if value is None:
                    missing.append(field_name)
        if missing:
            raise ValueError(
                f"Calculation window '{self.title}' is missing required field(s): {', '.join(missing)}"
            )


@dataclass(slots=True)
class LegacyCalculationWindow:
    """Backward-compatible legacy format used by older page code."""

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


def adapt_legacy_window(window: LegacyCalculationWindow) -> CalculationWindow:
    """Adapt a legacy calculation window to the rich pedagogical schema."""
    sign_notes = tuple(window.sign_convention_notes)
    assumptions = tuple(window.assumptions) or ("No additional assumptions provided.",)
    return CalculationWindow(
        title=window.title,
        concept_meaning=f"{window.title} explains one component of the pricing decomposition.",
        why_it_matters="It links observable market inputs to a decision-relevant metric.",
        formula=window.formula,
        methodology_rationale="Apply the stated identity under the page sign convention.",
        inputs_used=window.substituted_values,
        substituted_values=window.substituted_values,
        derivation_steps=(
            "Read market inputs under the HUF-per-USD convention.",
            "Apply the formula directly.",
            "Compare against benchmark interpretation.",
        ),
        assumptions=assumptions,
        interpretation=sign_notes[0] if sign_notes else "Interpret result under the page sign convention.",
        common_misunderstandings=sign_notes or ("Ignoring sign conventions can invert interpretation.",),
        result=window.result,
        expanded=window.expanded,
    )


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


def _normalize_window(window: CalculationWindow | LegacyCalculationWindow) -> CalculationWindow:
    if isinstance(window, CalculationWindow):
        return window
    if isinstance(window, LegacyCalculationWindow):
        return adapt_legacy_window(window)
    raise TypeError(f"Expected CalculationWindow or LegacyCalculationWindow, got {type(window)!r}.")


def render_calculation_window(window: CalculationWindow | LegacyCalculationWindow) -> None:
    """Render a single collapsible window containing a calculation breakdown."""
    import streamlit as st

    normalized = _normalize_window(window)
    with st.expander(normalized.title, expanded=normalized.expanded):
        st.markdown("#### Concept")
        st.markdown(normalized.concept_meaning)

        st.markdown("#### Why it matters")
        st.markdown(normalized.why_it_matters)

        st.markdown("#### Formula")
        st.latex(normalized.formula)

        st.markdown("#### Method")
        st.markdown(normalized.methodology_rationale)

        st.markdown("#### Inputs")
        st.markdown(normalized.inputs_used)

        st.markdown("#### Substitution")
        st.markdown(normalized.substituted_values)

        st.markdown("#### Derivation")
        for step in normalized.derivation_steps:
            st.markdown(f"- {step}")

        if normalized.deep_derivation:
            with st.expander("Derivation details", expanded=False):
                for detail in normalized.deep_derivation:
                    st.markdown(f"- {detail}")

        st.markdown("#### Assumptions")
        if normalized.assumptions:
            for assumption in normalized.assumptions:
                st.markdown(f"- {assumption}")
        else:
            st.markdown("- None provided")

        st.markdown("#### Interpretation")
        st.markdown(normalized.interpretation)

        st.markdown("#### Common misunderstandings")
        if normalized.common_misunderstandings:
            for misunderstanding in normalized.common_misunderstandings:
                st.markdown(f"- {misunderstanding}")
        else:
            st.markdown("- None provided")

        st.markdown("#### Result")
        st.success(normalized.result)


def render_calculation_windows(windows: Iterable[CalculationWindow | LegacyCalculationWindow]) -> None:
    """Render a list of collapsible calculation windows."""
    for window in windows:
        render_calculation_window(_apply_sign_context(window, sign_convention))


def render_required_calculation_windows(
    calculations: dict[str, CalculationWindow | LegacyCalculationWindow],
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
        window = _normalize_window(calculations[key])
        window.validate()
        if window.expanded != default_expanded:
            windows.append(window)
        else:
            windows.append(
                CalculationWindow(
                    title=window.title,
                    concept_meaning=window.concept_meaning,
                    why_it_matters=window.why_it_matters,
                    formula=window.formula,
                    methodology_rationale=window.methodology_rationale,
                    inputs_used=window.inputs_used,
                    substituted_values=window.substituted_values,
                    derivation_steps=tuple(window.derivation_steps),
                    deep_derivation=tuple(window.deep_derivation),
                    assumptions=tuple(window.assumptions),
                    interpretation=window.interpretation,
                    common_misunderstandings=tuple(window.common_misunderstandings),
                    result=window.result,
                    expanded=default_expanded,
                )
            )

    render_calculation_windows(windows, sign_convention=sign_convention)
