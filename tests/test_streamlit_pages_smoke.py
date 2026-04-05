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

    def _record_markdown(text, *args, **kwargs):
        stub.markdown_calls.append(str(text))

    stub.set_page_config = lambda *a, **k: None
    stub.title = lambda *a, **k: None
    stub.caption = lambda *a, **k: None
    stub.markdown = _record_markdown
    stub.write = lambda *a, **k: None
    stub.metric = lambda *a, **k: None
    stub.line_chart = lambda *a, **k: None
    stub.dataframe = lambda *a, **k: None
    stub.latex = lambda *a, **k: None
    stub.success = lambda *a, **k: None
    stub.info = lambda *a, **k: None
    stub.header = lambda *a, **k: None
    stub.subheader = lambda *a, **k: None
    stub.divider = lambda *a, **k: None
    stub.segmented_control = lambda label, options, default=None, **k: default or options[0]
    stub.slider = lambda label, min_value, max_value, value, *a, **k: value
    stub.number_input = lambda label, **k: k.get("value", 1.0)
    stub.selectbox = lambda label, options, index=0, **k: options[index]
    stub.columns = lambda n, *a, **k: [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]
    stub.expander = lambda *a, **k: _Ctx()
    stub.sidebar = _Ctx()
    return stub


@pytest.mark.parametrize(
    "module_name",
    [
        "app",
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
    monkeypatch.setitem(sys.modules, "streamlit", stub)

    module = importlib.import_module(module_name)
    importlib.reload(module)

    assert "cross_currency_basis_bps" in stub.session_state
    assert "suggested_page" in stub.session_state


def test_calculation_panel_sections_present(monkeypatch):
    stub = _build_streamlit_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub)

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
