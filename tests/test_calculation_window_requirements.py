from __future__ import annotations

import ast
from pathlib import Path

import pytest

from streamlit_calc_helpers import CalculationWindow, validate_required_calculation_windows
from streamlit_calc_helpers import CALCULATION_KEY_TO_TITLE, SECTION_ORDER


PAGE_FILES = [
    Path("pages/2_XCCY_mechanics.py"),
    Path("pages/3_Parity_lab.py"),
    Path("pages/4_Market_basis_and_funding_transformation.py"),
    Path("pages/5_Persistence_XVA_arbitrage_limits.py"),
    Path("pages/6_Hedged_pickup_and_hedge_choice.py"),
    Path("pages/7_HUF_USD_strategy_and_stress_lab.py"),
]


def _valid_window(title: str) -> CalculationWindow:
    return CalculationWindow(
        title=title,
        concept=title,
        meaning="Meaning",
        significance="Significance",
        formula="x",
        methodology="Methodology",
        inputs="Inputs",
        substituted_values="Substitution",
        derivation_steps=("Step",),
        assumptions=("Assumption",),
        interpretation="Interpretation",
        common_misunderstandings=("Misunderstanding",),
        result="Result",
    )


def _extract_required_keys(page_file: Path) -> tuple[str, ...]:
    tree = ast.parse(page_file.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != "REQUIRED_CALCULATION_WINDOWS":
            continue
        if not isinstance(node.value, ast.Tuple):
            raise AssertionError(f"{page_file} REQUIRED_CALCULATION_WINDOWS must be a tuple literal")
        keys: list[str] = []
        for elt in node.value.elts:
            if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                raise AssertionError(f"{page_file} REQUIRED_CALCULATION_WINDOWS values must be strings")
            keys.append(elt.value)
        return tuple(keys)
    raise AssertionError(f"{page_file} is missing REQUIRED_CALCULATION_WINDOWS")


@pytest.mark.parametrize("page_file", PAGE_FILES)
def test_page_declares_required_calculation_windows(page_file: Path) -> None:
    keys = _extract_required_keys(page_file)

    assert keys
    assert all(isinstance(key, str) for key in keys)
    unknown = [key for key in keys if key not in CALCULATION_KEY_TO_TITLE]
    assert not unknown, f"{page_file} has unknown calculation window keys: {unknown}"


@pytest.mark.parametrize("section_name", SECTION_ORDER)
def test_calculation_window_section_contract_contains_expected_sections(section_name: str) -> None:
    assert section_name in SECTION_ORDER


def test_parity_page_required_windows_match_page_scope() -> None:
    keys = _extract_required_keys(Path("pages/3_Parity_lab.py"))
    assert keys == (
        "theoretical_forward",
        "implied_huf_rate",
        "implied_usd_rate",
        "forward_difference",
        "relative_forward_difference",
        "raw_basis_wedge",
    )


def test_validator_only_requires_active_page_windows() -> None:
    parity_keys = (
        "theoretical_forward",
        "implied_huf_rate",
        "implied_usd_rate",
        "forward_difference",
        "relative_forward_difference",
        "raw_basis_wedge",
    )
    calculations = {key: _valid_window(key.replace("_", " ").title()) for key in parity_keys}

    windows = validate_required_calculation_windows(
        calculations,
        required_keys=parity_keys,
        page_name="3. Parity lab",
    )
    assert len(windows) == len(parity_keys)


def test_validator_raises_descriptive_error_on_missing_required_key() -> None:
    with pytest.raises(KeyError) as exc:
        validate_required_calculation_windows(
            {
                "theoretical_forward": _valid_window("Theoretical forward"),
                "implied_huf_rate": _valid_window("Implied HUF rate"),
            },
            required_keys=("theoretical_forward", "implied_huf_rate", "raw_basis_wedge"),
            page_name="3. Parity lab",
        )

    message = str(exc.value)
    assert "3. Parity lab" in message
    assert "raw_basis_wedge" in message
    assert "Provided keys" in message


def test_validator_fails_if_any_required_field_is_missing() -> None:
    window = _valid_window("Theoretical forward")
    window.result = ""

    with pytest.raises(ValueError, match=r"Theoretical forward.*result"):
        validate_required_calculation_windows(
            {"theoretical_forward": window},
            required_keys=("theoretical_forward",),
            page_name="2. XCCY mechanics",
        )
