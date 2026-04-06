"""Shared Streamlit helpers for collapsible calculation windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass(slots=True, kw_only=True)
class CalculationWindow:
    """Pedagogical container for calculation details displayed in the UI."""

    concept: str = ""
    meaning: str = ""
    significance: str = ""
    formula: str = ""
    methodology: str = ""
    inputs: str = ""
    substituted_values: str = ""
    derivation_steps: Sequence[str] = field(default_factory=tuple)
    assumptions: Sequence[str] = field(default_factory=tuple)
    interpretation: str = ""
    common_misunderstandings: Sequence[str] = field(default_factory=tuple)
    result: str = ""
    title: str | None = None
    expanded: bool = False

    def __post_init__(self) -> None:
        # Clean aliasing between concept and optional UI title.
        if (not self.concept or not self.concept.strip()) and self.title and self.title.strip():
            self.concept = self.title
        if self.title is None or not self.title.strip():
            self.title = self.concept

        self.derivation_steps = tuple(self.derivation_steps)
        self.assumptions = tuple(self.assumptions)
        self.common_misunderstandings = tuple(self.common_misunderstandings)

    def validate(self, *, required_fields: Sequence[str] | None = None) -> None:
        """Validate required narrative sections are populated."""
        required = tuple(
            required_fields
            or (
                "concept",
                "meaning",
                "significance",
                "formula",
                "methodology",
                "inputs",
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


@dataclass(frozen=True, slots=True)
class SignConventionContext:
    """Shared sign-convention details applied to a page's calculation windows."""

    quote_convention: str
    perspective: str
    positive_interpretation: str
    negative_interpretation: str


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

DEFAULT_REQUIRED_KEYS: tuple[str, ...] = (
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

SECTION_ORDER: tuple[str, ...] = (
    "Concept",
    "Meaning",
    "Significance",
    "Formula",
    "Methodology",
    "Inputs",
    "Substitution",
    "Derivation",
    "Assumptions",
    "Interpretation",
    "Common misunderstandings",
    "Result",
)


def _normalize_window(window: CalculationWindow) -> CalculationWindow:
    if isinstance(window, CalculationWindow):
        return window
    raise TypeError(f"Expected CalculationWindow, got {type(window)!r}.")


def _apply_sign_context(window: CalculationWindow, sign_convention: SignConventionContext | None) -> CalculationWindow:
    if sign_convention is None:
        return window

    interpretation = window.interpretation.strip() if window.interpretation else ""
    if not interpretation:
        interpretation = sign_convention.perspective

    assumptions = tuple(window.assumptions)
    if len(assumptions) == 0 or all(not str(item).strip() for item in assumptions):
        assumptions = (
            f"Quote convention is {sign_convention.quote_convention}.",
            f"Perspective: {sign_convention.perspective}",
        )

    return CalculationWindow(
        title=window.title,
        concept=window.concept,
        meaning=window.meaning,
        significance=window.significance,
        formula=window.formula,
        methodology=window.methodology,
        inputs=window.inputs,
        substituted_values=window.substituted_values,
        derivation_steps=tuple(window.derivation_steps),
        assumptions=assumptions,
        interpretation=interpretation,
        common_misunderstandings=tuple(window.common_misunderstandings),
        result=window.result,
        expanded=window.expanded,
    )


def validate_required_calculation_windows(
    calculations: dict[str, CalculationWindow],
    *,
    required_keys: Sequence[str],
    page_name: str | None = None,
    default_expanded: bool = False,
) -> list[CalculationWindow]:
    """Validate required calculation windows and return normalized windows."""
    missing = [key for key in required_keys if key not in calculations]
    if missing:
        scope = page_name or "current page"
        raise KeyError(
            f"{scope}: missing required calculation window key(s): {', '.join(missing)}. "
            f"Provided keys: {', '.join(sorted(calculations))}"
        )

    windows: list[CalculationWindow] = []
    for key in required_keys:
        window = _normalize_window(calculations[key])
        window.validate()
        normalized_expanded = default_expanded if window.expanded is False else window.expanded
        windows.append(
            CalculationWindow(
                title=window.title,
                concept=window.concept,
                meaning=window.meaning,
                significance=window.significance,
                formula=window.formula,
                methodology=window.methodology,
                inputs=window.inputs,
                substituted_values=window.substituted_values,
                derivation_steps=tuple(window.derivation_steps),
                assumptions=tuple(window.assumptions),
                interpretation=window.interpretation,
                common_misunderstandings=tuple(window.common_misunderstandings),
                result=window.result,
                expanded=normalized_expanded,
            )
        )
    return windows


def render_calculation_window(window: CalculationWindow) -> None:
    """Render a single collapsible window containing a calculation breakdown."""
    import streamlit as st

    normalized = _normalize_window(window)
    with st.expander(normalized.title, expanded=normalized.expanded):
        st.markdown("#### Concept")
        st.markdown(normalized.concept)

        st.markdown("#### Meaning")
        st.markdown(normalized.meaning)

        st.markdown("#### Significance")
        st.markdown(normalized.significance)

        st.markdown("#### Formula")
        st.latex(normalized.formula)

        st.markdown("#### Methodology")
        st.markdown(normalized.methodology)

        st.markdown("#### Inputs")
        st.markdown(normalized.inputs)

        st.markdown("#### Substitution")
        st.markdown(normalized.substituted_values)

        st.markdown("#### Derivation")
        for step in normalized.derivation_steps:
            st.markdown(f"- {step}")

        st.markdown("#### Assumptions")
        for assumption in normalized.assumptions:
            st.markdown(f"- {assumption}")

        st.markdown("#### Interpretation")
        st.markdown(normalized.interpretation)

        st.markdown("#### Common misunderstandings")
        for misunderstanding in normalized.common_misunderstandings:
            st.markdown(f"- {misunderstanding}")

        st.markdown("#### Result")
        st.success(normalized.result)


def render_calculation_windows(
    windows: Iterable[CalculationWindow],
    *,
    sign_convention: SignConventionContext | None = None,
) -> None:
    """Render a list of collapsible calculation windows."""
    for window in windows:
        normalized = _normalize_window(window)
        render_calculation_window(_apply_sign_context(normalized, sign_convention))


def render_required_calculation_windows(
    calculations: dict[str, CalculationWindow],
    *,
    required_keys: Sequence[str] = DEFAULT_REQUIRED_KEYS,
    page_name: str | None = None,
    default_expanded: bool = False,
    sign_convention: SignConventionContext | None = None,
) -> None:
    """Render all required windows in a consistent order."""
    windows = validate_required_calculation_windows(
        calculations,
        required_keys=required_keys,
        page_name=page_name,
        default_expanded=default_expanded,
    )
    render_calculation_windows(windows, sign_convention=sign_convention)


def render_shared_sign_convention(context: SignConventionContext) -> None:
    """Render a standardized sign-convention block used across pages."""
    import streamlit as st

    st.markdown("### Sign convention")
    st.markdown(f"- **Quote convention:** {context.quote_convention}")
    st.markdown(f"- **Perspective:** {context.perspective}")
    st.markdown(f"- **Positive interpretation:** {context.positive_interpretation}")
    st.markdown(f"- **Negative interpretation:** {context.negative_interpretation}")
