from __future__ import annotations

import importlib
import inspect
import pkgutil
import random
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


CANDIDATE_MODULES = {
    "generator": ["xccy.generator", "src.generator", "app.generator", "generator"],
    "parity": ["xccy.parity", "src.parity", "app.parity", "parity"],
    "basis": ["xccy.basis", "src.basis", "app.basis", "basis"],
    "conversion_factor": ["xccy.conversion_factor", "src.conversion_factor", "app.conversion_factor", "conversion_factor"],
    "arbitrage_band": ["xccy.arbitrage_band", "src.arbitrage_band", "app.arbitrage_band", "arbitrage_band"],
    "scenario_application": ["xccy.scenario_application", "src.scenario_application", "app.scenario_application", "scenario_application"],
    "narrative_engine": ["xccy.narrative_engine", "src.narrative_engine", "app.narrative_engine", "narrative_engine"],
}


def deterministic_rng(seed: int = 20260405) -> random.Random:
    return random.Random(seed)


def synthetic_market_rows(n: int = 200, seed: int = 20260405) -> dict[str, list[float]]:
    rng = deterministic_rng(seed)
    spreads = [rng.gauss(0.0, 40.0) for _ in range(n)]
    rates = [rng.gauss(2.5, 1.2) for _ in range(n)]
    liquidity = [max(0.01, rng.lognormvariate(1.5, 0.7)) for _ in range(n)]
    return {"spreads_bps": spreads, "rates_pct": rates, "liquidity": liquidity}


def try_import_any(candidates: Iterable[str]):
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def find_repo_python_modules() -> list[str]:
    modules: list[str] = []
    for py_file in REPO_ROOT.rglob("*.py"):
        if ".git" in py_file.parts or "tests" in py_file.parts:
            continue
        if py_file.name.startswith("_"):
            continue
        rel = py_file.relative_to(REPO_ROOT)
        modules.append(".".join(rel.with_suffix("").parts))

    for info in pkgutil.iter_modules([str(REPO_ROOT)]):
        modules.append(info.name)

    return sorted(set(modules))


def public_callables(module: Any) -> dict[str, Any]:
    return {
        name: obj
        for name, obj in inspect.getmembers(module)
        if callable(obj) and not name.startswith("_")
    }
