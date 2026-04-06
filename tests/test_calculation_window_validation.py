from __future__ import annotations

import pytest

from streamlit_calc_helpers import CalculationWindow, SECTION_ORDER, render_calculation_window, render_required_calculation_windows


def _valid_window(title: str) -> CalculationWindow:
    return CalculationWindow(
        title=title,
        concept=title,
        meaning="Concept",
        significance="Why",
        formula="x",
        methodology="Method",
        inputs="Inputs",
        substituted_values="Substitution",
        derivation_steps=("Step 1",),
        assumptions=("Assumption",),
        interpretation="Interpretation",
        common_misunderstandings=("Misunderstanding",),
        result="Result",
    )


@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("concept", " "),
        ("meaning", " "),
        ("significance", " "),
        ("formula", " "),
        ("methodology", " "),
        ("inputs", " "),
        ("substituted_values", " "),
        ("derivation_steps", tuple()),
        ("assumptions", tuple()),
        ("interpretation", " "),
        ("common_misunderstandings", tuple()),
        ("result", " "),
    ],
)
def test_validate_fails_when_any_required_field_missing(field_name: str, bad_value: object) -> None:
    window = _valid_window("Core")
    setattr(window, field_name, bad_value)

    with pytest.raises(ValueError, match=rf"Core.*{field_name}"):
        window.validate()


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
    window.significance = "   "

    with pytest.raises(ValueError, match=r"Core.*significance"):
        window.validate()


def test_required_calculation_windows_fail_loudly_for_blank_core_section() -> None:
    windows = _valid_required_windows()
    windows["theoretical_forward"].meaning = ""

    with pytest.raises(ValueError, match=r"Theoretical forward.*meaning"):
        render_required_calculation_windows(windows)


def test_render_calculation_window_preserves_section_order(monkeypatch: pytest.MonkeyPatch) -> None:
    section_calls: list[str] = []

    class _DummyExpander:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class _DummyStreamlit:
        def expander(self, *_args, **_kwargs):
            return _DummyExpander()

        def markdown(self, value: str):
            if value.startswith("#### "):
                section_calls.append(value.replace("#### ", ""))

        def latex(self, _value: str):
            return None

        def success(self, _value: str):
            return None

    import sys

    monkeypatch.setitem(sys.modules, "streamlit", _DummyStreamlit())
    render_calculation_window(_valid_window("Ordered"))

    assert tuple(section_calls) == SECTION_ORDER
