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
    ]
    shell.learning_hint = lambda *a, **k: None
    shell.render_global_shell = lambda *a, **k: None
    return shell


@pytest.mark.parametrize(
    "module_name",
    [
        "pages.2_XCCY_mechanics",
        "pages.3_Parity_lab",
        "pages.4_Market_basis_and_funding_transformation",
        "pages.5_Persistence_XVA_arbitrage_limits",
        "pages.6_Hedged_pickup_and_hedge_choice",
        "pages.7_HUF_USD_strategy_and_stress_lab",
    ],
)
def test_each_page_imports_and_renders_with_mocked_market_state(monkeypatch, module_name):
    stub = _build_streamlit_stub()
    shell_stub = _build_ui_shell_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setitem(sys.modules, "ui_shell", shell_stub)
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

    windows = {
        "theoretical_forward": CalculationWindow("Theoretical forward", "x", "x"),
        "implied_huf_rate": CalculationWindow("Implied HUF rate", "x", "x"),
        "implied_usd_rate": CalculationWindow("Implied USD rate", "x", "x"),
        "raw_basis_wedge": CalculationWindow("Raw basis wedge", "x", "x"),
        "synthetic_funding_cost": CalculationWindow("Synthetic funding cost", "x", "x"),
        "friction_adjusted_arbitrage_band": CalculationWindow("Friction-adjusted arbitrage band", "x", "x"),
        "hedged_pickup": CalculationWindow("Hedged pickup", "x", "x"),
        "conversion_factor": CalculationWindow("Conversion factor", "x", "x"),
        "stressed_vs_base_deltas": CalculationWindow("Stressed vs base deltas", "x", "x"),
    }

    render_required_calculation_windows(windows)

    body = "\n".join(stub.markdown_calls)
    assert "**Formula**" in body
    assert "**Substituted values**" in body
    assert "**Sign convention notes**" in body
    assert "**Assumptions**" in body
    assert "**Result**" in body


def test_required_calculation_windows_render_in_canonical_order(monkeypatch):
    stub = _build_streamlit_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    sys.modules.pop("streamlit_calc_helpers", None)

    from streamlit_calc_helpers import CalculationWindow, DEFAULT_CALCULATION_TITLES, render_required_calculation_windows

    windows = {
        "theoretical_forward": CalculationWindow("Theoretical forward", "x", "x"),
        "implied_huf_rate": CalculationWindow("Implied HUF rate", "x", "x"),
        "implied_usd_rate": CalculationWindow("Implied USD rate", "x", "x"),
        "raw_basis_wedge": CalculationWindow("Raw basis wedge", "x", "x"),
        "synthetic_funding_cost": CalculationWindow("Synthetic funding cost", "x", "x"),
        "friction_adjusted_arbitrage_band": CalculationWindow("Friction-adjusted arbitrage band", "x", "x"),
        "hedged_pickup": CalculationWindow("Hedged pickup", "x", "x"),
        "conversion_factor": CalculationWindow("Conversion factor", "x", "x"),
        "stressed_vs_base_deltas": CalculationWindow("Stressed vs base deltas", "x", "x"),
    }

    render_required_calculation_windows(windows)
    assert tuple(stub.expander_labels) == DEFAULT_CALCULATION_TITLES


def test_required_calculation_windows_raise_loudly_when_key_missing(monkeypatch):
    stub = _build_streamlit_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    sys.modules.pop("streamlit_calc_helpers", None)

    from streamlit_calc_helpers import CalculationWindow, render_required_calculation_windows

    windows = {
        "theoretical_forward": CalculationWindow("Theoretical forward", "x", "x"),
        "implied_huf_rate": CalculationWindow("Implied HUF rate", "x", "x"),
        "implied_usd_rate": CalculationWindow("Implied USD rate", "x", "x"),
        "raw_basis_wedge": CalculationWindow("Raw basis wedge", "x", "x"),
        "synthetic_funding_cost": CalculationWindow("Synthetic funding cost", "x", "x"),
        "friction_adjusted_arbitrage_band": CalculationWindow("Friction-adjusted arbitrage band", "x", "x"),
        "hedged_pickup": CalculationWindow("Hedged pickup", "x", "x"),
        "conversion_factor": CalculationWindow("Conversion factor", "x", "x"),
    }

    with pytest.raises(KeyError, match=r"Missing required calculation window: 'stressed_vs_base_deltas'"):
        render_required_calculation_windows(windows)


@pytest.mark.parametrize(
    "page_file,conceptual_intro,why_it_matters,derivation_markers",
    [
        (
            "pages/2_XCCY_mechanics.py",
            "Mechanics are shown from the USD-receiver / HUF-payer perspective.",
            "Positive cashflows are received by the USD leg receiver.",
            ("Synthetic USD (no basis)", "Synthetic USD (with basis)", "Basis drag"),
        ),
        (
            "pages/3_Parity_lab.py",
            "Observed forwards are benchmarked versus no-basis CIP fair values.",
            "Persistent wedge signals parity stress.",
            ("Theoretical forward", "Implied HUF rate", "Raw basis wedge"),
        ),
        (
            "pages/4_Market_basis_and_funding_transformation.py",
            "Funding transformation compares domestic route versus foreign-plus-basis route.",
            "Positive gap means synthetic route is less economical.",
            ("Domestic all-in", "Synthetic all-in", "Cross-market gap"),
        ),
        (
            "pages/5_Persistence_XVA_arbitrage_limits.py",
            "If the raw edge stays within the friction band, dislocations can persist.",
            "Capacity and XVA multipliers control when arbitrage is truly executable.",
            ("Total friction", "Net edge", "Actionability"),
        ),
        (
            "pages/6_Hedged_pickup_and_hedge_choice.py",
            "Hedge choice is based on risk-adjusted pickup rather than carry alone.",
            "Rolling hedges can lose after volatility-scaled roll risk penalties.",
            ("Simple conversion factor", "Pickup decomposition", "Matched vs rolling hedge"),
        ),
        (
            "pages/7_HUF_USD_strategy_and_stress_lab.py",
            "Stress scenarios roll into CIP wedge, funding transformation, frictions, and hedge economics.",
            "Check whether net pickup survives widened friction bands and whether hedge preference flips.",
            ("Stressed CIP wedge", "Stressed hedged pickup", "Stressed preferred hedge choice"),
        ),
    ],
)
def test_page_has_intro_why_and_derivation_markers(page_file, conceptual_intro, why_it_matters, derivation_markers):
    import pathlib

    body = pathlib.Path(page_file).read_text()
    assert conceptual_intro in body
    assert why_it_matters in body
    for marker in derivation_markers:
        assert marker in body


def test_required_core_concept_windows_do_not_use_placeholder_na():
    import pathlib
    import re

    page_text = pathlib.Path("pages/3_Parity_lab.py").read_text()
    disallowed_placeholder = "N/A on this page"
    required_core_keys = (
        "theoretical_forward",
        "implied_huf_rate",
        "implied_usd_rate",
        "raw_basis_wedge",
        "synthetic_funding_cost",
        "conversion_factor",
    )

    for key in required_core_keys:
        pattern = rf'"{key}"\s*:\s*CalculationWindow\((?P<body>.*?)\),\n\s*"'
        match = re.search(pattern, page_text, flags=re.DOTALL)
        assert match is not None, f"Expected required core window '{key}' in parity page payload."
        assert disallowed_placeholder not in match.group("body")


def test_page3_worked_example_renders_substitution_and_stepwise_derivation():
    import pathlib

    body = pathlib.Path("pages/3_Parity_lab.py").read_text()
    assert 'button("Worked example (HUF/USD)")' in body
    assert 'f"$S={spot:.4f}, r_{{HUF}}={huf_rate:.4%}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$"' in body
    assert 'f"$F={observed_forward:.4f}, S={spot:.4f}, r_{{USD}}={usd_rate:.4%}, T={tenor_years:.2f}$"' in body
    assert '"**Formula**"' in pathlib.Path("streamlit_calc_helpers.py").read_text()
    assert '"**Substituted values**"' in pathlib.Path("streamlit_calc_helpers.py").read_text()
    assert '"**Result**"' in pathlib.Path("streamlit_calc_helpers.py").read_text()
