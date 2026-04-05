from __future__ import annotations

import importlib
from pathlib import Path

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


@pytest.mark.parametrize("module_name", _discover_page_modules())
def test_streamlit_page_module_imports_and_has_public_callable(module_name: str):
    mod = importlib.import_module(module_name)
    cbs = public_callables(mod)
    assert cbs, f"Expected at least one public callable in {module_name}"


def test_streamlit_pages_discovery_does_not_error_when_pages_missing():
    # This is intentionally permissive: repos without Streamlit pages should not fail.
    modules = _discover_page_modules()
    assert isinstance(modules, list)
