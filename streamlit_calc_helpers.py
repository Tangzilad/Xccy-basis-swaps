"""Shared Streamlit helpers for collapsible calculation windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass(slots=True)
class CalculationWindow:
    """Pedagogical container for calculation details displayed in the UI.

    Supports both the rich schema used by newer pages and a compact legacy
    positional form:
    ``CalculationWindow(title, formula, substituted_values, sign_notes=..., result=...)``.
    """

    title: str
    concept_meaning: str = ""
    why_it_matters: str = ""
    formula: str = ""
    methodology_rationale: str = ""
    inputs_used: str = ""
    substituted_values: str = ""
    derivation_steps: Sequence[str] = field(default_factory=tuple)
    deep_derivation: Sequence[str] = field(default_factory=tuple)
    assumptions: Sequence[str] = field(default_factory=tuple)
    interpretation: str = ""
    common_misunderstandings: Sequence[str] = field(default_factory=tuple)
    result: str = ""
    expanded: bool = False

    def __init__(self, title: str, *args, **kwargs) -> None:  # noqa: D401 - custom init for compatibility
        self.title = title

        # Defaults
        self.concept_meaning = kwargs.pop("concept_meaning", "")
        self.why_it_matters = kwargs.pop("why_it_matters", "")
        self.formula = kwargs.pop("formula", "")
        self.methodology_rationale = kwargs.pop("methodology_rationale", "")
        self.inputs_used = kwargs.pop("inputs_used", "")
        self.substituted_values = kwargs.pop("substituted_values", "")
        self.derivation_steps = tuple(kwargs.pop("derivation_steps", ()))
        self.deep_derivation = tuple(kwargs.pop("deep_derivation", ()))
        self.assumptions = tuple(kwargs.pop("assumptions", ()))
        self.interpretation = kwargs.pop("interpretation", "")
        self.common_misunderstandings = tuple(kwargs.pop("common_misunderstandings", ()))
        self.result = kwargs.pop("result", "")
        self.expanded = kwargs.pop("expanded", False)

        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise TypeError(f"Unknown CalculationWindow argument(s): {unknown}")

        # Legacy positional shape: (formula, substituted_values[, sign_notes])
        if len(args) >= 2 and not self.formula and not self.substituted_values:
            self.formula = str(args[0])
            self.substituted_values = str(args[1])
            self.inputs_used = self.inputs_used or self.substituted_values

            sign_notes: Sequence[str] = tuple(args[2]) if len(args) >= 3 else tuple()
            self.concept_meaning = self.concept_meaning or f"{title} explains one component of the pricing decomposition."
            self.why_it_matters = self.why_it_matters or "It links observable market inputs to a decision-relevant metric."
            self.methodology_rationale = self.methodology_rationale or "Apply the stated identity under the page sign convention."
            self.derivation_steps = self.derivation_steps or (
                "Read market inputs under the HUF-per-USD convention.",
                "Apply the formula directly.",
                "Compare against benchmark interpretation.",
            )
            self.assumptions = self.assumptions or ("No additional assumptions provided.",)
            self.interpretation = self.interpretation or (
                sign_notes[0] if sign_notes else "Interpret result under the page sign convention."
            )
            self.common_misunderstandings = self.common_misunderstandings or (
                sign_notes if sign_notes else ("Ignoring sign conventions can invert interpretation.",)
            )
            return

        # Compact positional shape used in tests: (formula, substituted_values)
        if len(args) == 2 and not self.formula and not self.substituted_values:
            self.formula = str(args[0])
            self.substituted_values = str(args[1])
            self.inputs_used = self.inputs_used or self.substituted_values

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


def adapt_legacy_window(window: LegacyCalculationWindow) -> CalculationWindow:
    """Adapt a legacy calculation window to the rich pedagogical schema."""
    return CalculationWindow(
        window.title,
        window.formula,
        window.substituted_values,
        tuple(window.sign_convention_notes),
        assumptions=tuple(window.assumptions),
        result=window.result,
        expanded=window.expanded,
    )


def _normalize_window(window: CalculationWindow | LegacyCalculationWindow) -> CalculationWindow:
    if isinstance(window, CalculationWindow):
        return window
    if isinstance(window, LegacyCalculationWindow):
        return adapt_legacy_window(window)
    raise TypeError(f"Expected CalculationWindow or LegacyCalculationWindow, got {type(window)!r}.")


def _apply_sign_context(window: CalculationWindow, sign_convention: SignConventionContext | None) -> CalculationWindow:
    if sign_convention is None:
        return window
    interpretation = window.interpretation or sign_convention.perspective
    misunderstandings = tuple(window.common_misunderstandings) or (
        f"Misreading the quote convention ({sign_convention.quote_convention}) can invert interpretation.",
    )
    assumptions = tuple(window.assumptions) or (f"Quote convention is {sign_convention.quote_convention}.",)

    return CalculationWindow(
        title=window.title,
        concept_meaning=window.concept_meaning,
        why_it_matters=window.why_it_matters,
        formula=window.formula,
        methodology_rationale=window.methodology_rationale,
        inputs_used=window.inputs_used,
        substituted_values=window.substituted_values,
        derivation_steps=tuple(window.derivation_steps),
        deep_derivation=tuple(window.deep_derivation),
        assumptions=assumptions,
        interpretation=interpretation,
        common_misunderstandings=misunderstandings,
        result=window.result,
        expanded=window.expanded,
    )


def validate_required_calculation_windows(
    calculations: dict[str, CalculationWindow | LegacyCalculationWindow],
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
                expanded=normalized_expanded,
            )
        )
    return windows


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


def render_calculation_windows(
    windows: Iterable[CalculationWindow | LegacyCalculationWindow],
    *,
    sign_convention: SignConventionContext | None = None,
) -> None:
    """Render a list of collapsible calculation windows."""
    for window in windows:
        normalized = _normalize_window(window)
        render_calculation_window(_apply_sign_context(normalized, sign_convention))


def render_required_calculation_windows(
    calculations: dict[str, CalculationWindow | LegacyCalculationWindow],
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
