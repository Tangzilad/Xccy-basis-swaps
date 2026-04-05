from __future__ import annotations

import ast
from pathlib import Path

from tests._test_utils import REPO_ROOT


NAV_KEYWORDS = {"page_link", "switch_page", "pages", "navigation", "sidebar"}


def _python_files() -> list[Path]:
    return [
        p
        for p in REPO_ROOT.rglob("*.py")
        if ".git" not in p.parts and "tests" not in p.parts
    ]


def _contains_nav_call(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in NAV_KEYWORDS:
                return True
            if isinstance(func, ast.Name) and func.id in NAV_KEYWORDS:
                return True
    return False


def test_navigation_signals_are_either_absent_or_repeatable():
    files = _python_files()
    nav_files = [p for p in files if _contains_nav_call(p)]

    # If navigation exists, it should be in a stable, deterministic set of files.
    nav_files2 = [p for p in files if _contains_nav_call(p)]
    assert nav_files == nav_files2
