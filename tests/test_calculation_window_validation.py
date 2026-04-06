from __future__ import annotations

import pytest

from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows


def _valid_window(title: str) -> CalculationWindow:
    return CalculationWindow(
        title=title,
        concept_meaning="Concept",
        why_it_matters="Why",
        formula="x",
        methodology_rationale="Method",
        inputs_used="Inputs",
        substituted_values="Substitution",
        derivation_steps=("Step 1",),
        assumptions=("Assumption",),
        interpretation="Interpretation",
        common_misunderstandings=("Misunderstanding",),
        result="Result",
    )


def _valid_required_windows() -> dict[str, CalculationWindow]:
    return {
        "theoretical_forward": _valid_window("Theoretical forward"),
        "implied_huf_rate": _valid_window("Implied HUF rate"),
        "implied_usd_rate": _valid_window("Implied USD rate"),
        "raw_basis_wedge": _valid_window("Raw basis wedge"),
        "synthetic_funding_cost": _valid_window("Synthetic funding cost"),
        "friction_adjusted_arbitrage_band": _valid_window("Friction-adjusted arbitrage band"),
        "hedged_pickup": _valid_window("Hedged pickup"),
        "conversion_factor": _valid_window("Conversion factor"),
        "stressed_vs_base_deltas": _valid_window("Stressed vs base deltas"),
    }


def test_validate_raises_clear_error_for_blank_required_string() -> None:
    window = _valid_window("Core")
    window.why_it_matters = "   "

    with pytest.raises(ValueError, match=r"Core.*why_it_matters"):
        window.validate()


def test_required_calculation_windows_fail_loudly_for_blank_core_section() -> None:
    windows = _valid_required_windows()
    windows["theoretical_forward"].concept_meaning = ""

    with pytest.raises(ValueError, match=r"Theoretical forward.*concept_meaning"):
        render_required_calculation_windows(windows)
