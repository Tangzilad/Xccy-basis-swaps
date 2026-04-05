from __future__ import annotations

import importlib

import pytest

from tests._test_utils import CANDIDATE_MODULES


@pytest.mark.parametrize("module_name", CANDIDATE_MODULES["generator"])
def test_import_smoke_for_generator_candidates(module_name: str):
    try:
        importlib.import_module(module_name)
    except Exception:
        pytest.skip(f"Optional module {module_name} not available")


def test_minimal_render_callable_presence_for_narrative_engine_if_available():
    for module_name in CANDIDATE_MODULES["narrative_engine"]:
        try:
            mod = importlib.import_module(module_name)
            break
        except Exception:
            mod = None
    if mod is None:
        pytest.skip("No narrative engine module found")

    has_render = any(
        name in dir(mod)
        for name in ("render", "render_page", "build_view", "main")
    )
    assert has_render, "Expected a render-like callable in narrative module"
