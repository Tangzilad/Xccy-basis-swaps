from __future__ import annotations

import importlib
import sys
import types

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None

    def write(self, *args, **kwargs):
        return None


def _build_streamlit_stub() -> types.ModuleType:
    stub = types.ModuleType("streamlit")
    stub.session_state = _SessionState(
        {
            "mode": "Learning",
            "base_rate": 4.25,
            "quote_rate": 5.0,
            "spot_fx": 1.08,
            "cross_currency_basis_bps": -22,
            "vol_regime": "Normal",
        }
    )
    stub.markdown_calls = []
    stub.write_calls = []
    stub.subheader_calls = []
    stub.expander_labels = []
    stub.text_area_calls = []
    stub.page_config_calls = 0
    stub._button_returns = {}

    def _record_markdown(text, *args, **kwargs):
        stub.markdown_calls.append(str(text))

    def _record_write(text, *args, **kwargs):
        stub.write_calls.append(str(text))

    def _record_subheader(text, *args, **kwargs):
        stub.subheader_calls.append(str(text))

    def _record_expander(label, *args, **kwargs):
        stub.expander_labels.append(str(label))
        return _Ctx()

    def _record_text_area(label, *args, **kwargs):
        stub.text_area_calls.append(str(label))
        return ""

    def _record_button(label, *args, **kwargs):
        return bool(stub._button_returns.get(label, False))

    def _record_page_config(*args, **kwargs):
        stub.page_config_calls += 1

    stub.set_page_config = _record_page_config
    stub.title = lambda *a, **k: None
    stub.caption = lambda *a, **k: None
    stub.markdown = _record_markdown
    stub.write = _record_write
    stub.metric = lambda *a, **k: None
    stub.line_chart = lambda *a, **k: None
    stub.bar_chart = lambda *a, **k: None
    stub.dataframe = lambda *a, **k: None
    stub.latex = lambda *a, **k: None
    stub.success = lambda *a, **k: None
    stub.info = lambda *a, **k: None
    stub.header = lambda *a, **k: None
    stub.subheader = _record_subheader
    stub.divider = lambda *a, **k: None
    stub.segmented_control = lambda label, options, default=None, **k: default or options[0]
    stub.slider = lambda label, min_value, max_value, value, *a, **k: value
    stub.number_input = lambda label, **k: k.get("value", 1.0)
    stub.selectbox = lambda label, options, index=0, **k: options[index]
    stub.columns = lambda n, *a, **k: [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]
    stub.expander = lambda *a, **k: _Ctx()
    stub.button = lambda *a, **k: False
    stub.text_input = lambda *a, **k: k.get("value", "")
    stub.error = lambda *a, **k: None
    stub.warning = lambda *a, **k: None
    stub.progress = lambda *a, **k: None
    stub.radio = lambda label, options, index=0, **k: options[index]

    sidebar = _Ctx()
    sidebar.markdown = lambda *a, **k: None
    sidebar.caption = lambda *a, **k: None
    sidebar.radio = lambda label, options, index=0, **k: options[index]
    sidebar.selectbox = lambda label, options, index=0, **k: options[index] if options else None
    sidebar.slider = lambda label, min_value=0, max_value=1, value=0.5, *a, **k: value
    sidebar.button = lambda *a, **k: False
    sidebar.progress = lambda *a, **k: None
    stub.sidebar = sidebar
    stub.expander = _record_expander
    stub.text_area = _record_text_area
    stub.button = _record_button
    stub.sidebar = _Ctx()
    return stub


def _build_ui_shell_stub() -> types.ModuleType:
    shell = types.ModuleType("ui_shell")
    shell.LEARNING_PATH = [
        "1. Start here",
        "2. XCCY mechanics",
        "3. Parity lab",
        "4. Market basis and funding transformation",
        "5. Persistence / XVA / arbitrage limits",
        "6. Hedged pickup and hedge choice",
        "7. HUF/USD strategy and stress lab",
        "8. Consolidated dashboard",
        "9. Glossary",
    ]
    shell.learning_hint = lambda *a, **k: None
    shell.render_global_shell = lambda *a, **k: None
    shell.ensure_market_state_initialized = lambda *a, **k: None
    return shell


def _build_shared_page_helpers_stub() -> types.ModuleType:
    helpers = types.ModuleType("shared_page_helpers")
    helpers.get_market_params = lambda ss: {
        "spot_fx": float(ss.get("spot_fx", 365.0)),
        "usd_rate": float(ss.get("base_rate", 4.25)) / 100.0,
        "huf_rate": float(ss.get("quote_rate", 5.0)) / 100.0,
        "basis_bps": float(ss.get("cross_currency_basis_bps", -22.0)),
    }
    helpers.get_funding_params = lambda ss: {
        **helpers.get_market_params(ss),
        "extra_spread_bps": 12.0,
    }
    helpers.as_decimal = lambda v: v / 100.0 if v > 1 else v
    helpers.from_decimal = lambda v: v * 100.0 if v < 1 else v
    helpers.render_learning_objectives = lambda *a, **k: None
    helpers.render_key_takeaways = lambda *a, **k: None
    helpers.render_comprehension_checks = lambda *a, **k: None
    helpers.render_page_header = lambda *a, **k: None
    helpers.render_page_footer = lambda *a, **k: None
    return helpers


@pytest.mark.parametrize(
    "module_name",
    [
        "pages.2_XCCY_mechanics",
        "pages.3_Parity_lab",
        "pages.4_Market_basis_and_funding_transformation",
        "pages.5_Persistence_XVA_arbitrage_limits",
        "pages.6_Hedged_pickup_and_hedge_choice",
        "pages.7_HUF_USD_strategy_and_stress_lab",
        "pages.8_Consolidated_dashboard",
        "pages.9_Glossary",
    ],
)
def test_each_page_imports_and_renders_with_mocked_market_state(monkeypatch, module_name):
    stub = _build_streamlit_stub()
    shell_stub = _build_ui_shell_stub()
    helpers_stub = _build_shared_page_helpers_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setitem(sys.modules, "ui_shell", shell_stub)
    monkeypatch.setitem(sys.modules, "shared_page_helpers", helpers_stub)
    sys.modules.pop(module_name, None)

    importlib.import_module(module_name)

    assert "cross_currency_basis_bps" in stub.session_state
    assert "suggested_page" in stub.session_state
    assert stub.page_config_calls == 1


def test_calculation_panel_sections_present(monkeypatch):
    stub = _build_streamlit_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    sys.modules.pop("streamlit_calc_helpers", None)

    from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows

    def _window(title: str) -> CalculationWindow:
        return CalculationWindow(
            title=title,
            concept_meaning="Concept",
            why_it_matters="Why",
            formula="x",
            methodology_rationale="Method",
            inputs_used="Inputs",
            substituted_values="x",
            derivation_steps=("Step",),
            assumptions=("Assumption",),
            interpretation="Interpretation",
            common_misunderstandings=("Misunderstanding",),
            result="Result",
        )

    windows = {
        "theoretical_forward": _window("Theoretical forward"),
        "implied_huf_rate": _window("Implied HUF rate"),
        "implied_usd_rate": _window("Implied USD rate"),
        "raw_basis_wedge": _window("Raw basis wedge"),
        "synthetic_funding_cost": _window("Synthetic funding cost"),
        "friction_adjusted_arbitrage_band": _window("Friction-adjusted arbitrage band"),
        "hedged_pickup": _window("Hedged pickup"),
        "conversion_factor": _window("Conversion factor"),
        "stressed_vs_base_deltas": _window("Stressed vs base deltas"),
    }

    render_required_calculation_windows(
        windows,
        required_keys=tuple(windows),
        page_name="smoke",
    )

    body = "\n".join(stub.markdown_calls)
    assert "#### Formula" in body
    assert "#### Substitution" in body
    assert "#### Assumptions" in body
    assert "#### Common misunderstandings" in body
    assert "#### Result" in body
