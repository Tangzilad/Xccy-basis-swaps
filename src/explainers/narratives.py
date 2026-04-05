"""Structured narrative explanations for state transitions.

This module provides reusable helpers that convert a previous/current state pair
into explanation payloads suitable for UI rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional


Role = str


@dataclass(frozen=True)
class InputChange:
    """One changed input between two states."""

    name: str
    previous: Any
    current: Any
    delta: Optional[float]


@dataclass(frozen=True)
class StructuredExplanation:
    """Canonical explanation payload for scenario transitions."""

    changed_inputs: List[InputChange]
    transmission_mechanism: str
    economic_channel: str
    role_interpretation: str
    inspect_next: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["changed_inputs"] = [asdict(change) for change in self.changed_inputs]
        return payload


@dataclass(frozen=True)
class ExplanationSpec:
    """Rule set used to generate structured explanations."""

    transmission_template: str
    economic_channel: str
    role_interpretations: Mapping[Role, str]
    inspect_next: str
    mechanism_formula: Optional[str] = None


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def diff_state(
    previous_state: Mapping[str, Any],
    current_state: Mapping[str, Any],
    include_keys: Optional[Iterable[str]] = None,
) -> List[InputChange]:
    """Return changed inputs between two state snapshots.

    Args:
        previous_state: Baseline values.
        current_state: New values.
        include_keys: Optional explicit subset of keys to evaluate.
    """

    keys = list(include_keys) if include_keys is not None else sorted(set(previous_state) | set(current_state))
    changes: List[InputChange] = []

    for key in keys:
        prev = previous_state.get(key)
        curr = current_state.get(key)
        if prev == curr:
            continue

        prev_num = _to_float(prev)
        curr_num = _to_float(curr)
        delta = None
        if prev_num is not None and curr_num is not None:
            delta = curr_num - prev_num

        changes.append(InputChange(name=key, previous=prev, current=curr, delta=delta))

    return changes


def _format_change(change: InputChange) -> str:
    if change.delta is None:
        return f"{change.name}: {change.previous} → {change.current}"
    direction = "increased" if change.delta > 0 else "decreased"
    return f"{change.name} {direction} by {change.delta:.6g} ({change.previous} → {change.current})"


def default_transmission_text(changes: List[InputChange], formula: Optional[str] = None) -> str:
    """Build a concise transmission narrative from changed inputs."""

    if not changes:
        return "No state inputs changed; valuation and carry channels remain unchanged."

    rendered = "; ".join(_format_change(c) for c in changes)
    if formula:
        return f"Input shock: {rendered}. Transmission follows {formula}."
    return f"Input shock: {rendered}. Transmission occurs through the model's pricing equations and hedge ratios."


def explain_transition(
    previous_state: Mapping[str, Any],
    current_state: Mapping[str, Any],
    role: Role,
    spec: ExplanationSpec,
    include_keys: Optional[Iterable[str]] = None,
    transmission_builder: Optional[Callable[[List[InputChange], Optional[str]], str]] = None,
) -> StructuredExplanation:
    """Generate a role-aware explanation payload for a state transition."""

    changes = diff_state(previous_state, current_state, include_keys=include_keys)
    transmission_fn = transmission_builder or default_transmission_text
    transmission = spec.transmission_template.strip() or transmission_fn(changes, spec.mechanism_formula)

    role_note = spec.role_interpretations.get(role, spec.role_interpretations.get("default", "Monitor net funding spread and hedge slippage."))

    return StructuredExplanation(
        changed_inputs=changes,
        transmission_mechanism=transmission,
        economic_channel=spec.economic_channel,
        role_interpretation=role_note,
        inspect_next=spec.inspect_next,
    )


def explain_transition_dict(
    previous_state: Mapping[str, Any],
    current_state: Mapping[str, Any],
    role: Role,
    spec: ExplanationSpec,
    include_keys: Optional[Iterable[str]] = None,
    transmission_builder: Optional[Callable[[List[InputChange], Optional[str]], str]] = None,
) -> Dict[str, Any]:
    """Dictionary wrapper around :func:`explain_transition` for web frameworks."""

    return explain_transition(
        previous_state=previous_state,
        current_state=current_state,
        role=role,
        spec=spec,
        include_keys=include_keys,
        transmission_builder=transmission_builder,
    ).to_dict()
