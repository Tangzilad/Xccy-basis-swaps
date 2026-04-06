from __future__ import annotations

import importlib
import sys
import types


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

    stub = types.ModuleType("streamlit")
    stub.session_state = _SessionState({"suggested_page": "1. Start here"})
    stub.set_page_config = lambda *a, **k: None
    stub.title = lambda *a, **k: None
    stub.caption = lambda *a, **k: None
    stub.markdown = lambda *a, **k: None
    stub.info = lambda *a, **k: None
    stub.text_input = lambda *a, **k: ""
    stub.expander = lambda *a, **k: _Ctx()
    return stub


def _build_ui_shell_stub() -> types.ModuleType:
    shell = types.ModuleType("ui_shell")
    shell.render_global_shell = lambda *a, **k: None
    shell.ensure_market_state_initialized = lambda *a, **k: None
    return shell


def _load_glossary(monkeypatch):
    monkeypatch.setitem(sys.modules, "streamlit", _build_streamlit_stub())
    monkeypatch.setitem(sys.modules, "ui_shell", _build_ui_shell_stub())
    sys.modules.pop("pages.9_Glossary", None)
    mod = importlib.import_module("pages.9_Glossary")
    return mod.GLOSSARY


def test_glossary_contains_required_new_or_expanded_terms(monkeypatch):
    glossary = _load_glossary(monkeypatch)
    terms = {entry["term"].lower() for entry in glossary}

    required_substrings = [
        "deposit spread vs swap spread",
        "cip deviation persistence",
        "conversion factor (cf)",
        "issuance decision inequalities",
        "maturity-matched vs rolling hedge trade-off",
        "xva bundle and arbitrage band",
    ]

    for required in required_substrings:
        assert any(required in term for term in terms), f"Missing glossary term: {required}"


def test_glossary_entries_link_to_specific_lesson_pages_2_to_8(monkeypatch):
    glossary = _load_glossary(monkeypatch)
    allowed_prefixes = tuple(f"{page}. " for page in range(2, 9))

    for entry in glossary:
        related_pages = entry.get("related_pages", [])
        assert related_pages, f"Term has no related page links: {entry['term']}"
        for page in related_pages:
            assert page.startswith(allowed_prefixes), (
                f"Related page must be a specific lesson page (2-8): {entry['term']} -> {page}"
            )
