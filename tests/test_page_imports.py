from __future__ import annotations

import importlib
import sys
import types

import pytest

from tests._test_utils import REPO_ROOT, public_callables


STREAMLIT_PAGE_ROOTS = [
    REPO_ROOT / "pages",
    REPO_ROOT / "app" / "pages",
]


def _discover_page_modules() -> list[str]:
    modules: list[str] = []
    for root in STREAMLIT_PAGE_ROOTS:
        if not root.exists():
            continue
        for py in root.glob("*.py"):
            if py.name.startswith("_"):
                continue
            rel = py.relative_to(REPO_ROOT).with_suffix("")
            modules.append(".".join(rel.parts))
    return sorted(set(modules))


def _build_streamlit_stub() -> types.ModuleType:
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

    stub = types.ModuleType("streamlit")
    stub.session_state = _SessionState(
        {
            "suggested_page": "1. Start here",
            "base_rate": 4.25,
            "quote_rate": 5.0,
            "spot_fx": 1.08,
            "cross_currency_basis_bps": -22,
            "vol_regime": "Normal",
            "mode": "Learning",
        }
    )
    stub.set_page_config = lambda *a, **k: None
    stub.title = lambda *a, **k: None
    stub.caption = lambda *a, **k: None
    stub.markdown = lambda *a, **k: None
    stub.write = lambda *a, **k: None
    stub.metric = lambda *a, **k: None
    stub.line_chart = lambda *a, **k: None
    stub.bar_chart = lambda *a, **k: None
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
    return stub


def _build_ui_shell_stub() -> types.ModuleType:
    shell = types.ModuleType("ui_shell")
    shell.LEARNING_PATH = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
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


@pytest.mark.parametrize("module_name", _discover_page_modules())
def test_streamlit_page_module_imports_and_has_public_callable(module_name: str, monkeypatch):
    monkeypatch.setitem(sys.modules, "streamlit", _build_streamlit_stub())
    monkeypatch.setitem(sys.modules, "ui_shell", _build_ui_shell_stub())
    monkeypatch.setitem(sys.modules, "shared_page_helpers", _build_shared_page_helpers_stub())
    sys.modules.pop(module_name, None)
    mod = importlib.import_module(module_name)
    cbs = public_callables(mod)
    assert cbs, f"Expected at least one public callable in {module_name}"


def test_streamlit_pages_discovery_does_not_error_when_pages_missing():
    # This is intentionally permissive: repos without Streamlit pages should not fail.
    modules = _discover_page_modules()
    assert isinstance(modules, list)
