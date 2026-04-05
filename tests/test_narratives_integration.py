from __future__ import annotations

from src.explainers.narratives import ExplanationSpec, diff_state, explain_transition_dict


def test_narratives_detect_state_diffs(base_snapshot: dict, stress_snapshot: dict):
    changes = diff_state(base_snapshot, stress_snapshot)

    changed_names = {c.name for c in changes}
    assert "spot" in changed_names
    assert "basis_curve" in changed_names
    assert "capital_xva_proxy" in changed_names


def test_narratives_include_role_specific_output_fields(base_snapshot: dict, stress_snapshot: dict):
    spec = ExplanationSpec(
        transmission_template="",
        economic_channel="Funding stress widens synthetic funding costs and weakens actionability.",
        role_interpretations={
            "trader": "Focus on near-tenor basis convexity and execution slippage.",
            "risk": "Track limits utilization and downside carry asymmetry.",
            "default": "Monitor cross-market basis drift.",
        },
        inspect_next="Compare stressed net edge vs friction band by tenor.",
        mechanism_formula="F = S*(1+r_HUF*T)/(1+r_USD*T)",
    )

    trader_payload = explain_transition_dict(base_snapshot, stress_snapshot, role="trader", spec=spec)
    risk_payload = explain_transition_dict(base_snapshot, stress_snapshot, role="risk", spec=spec)

    assert set(trader_payload) == {
        "changed_inputs",
        "transmission_mechanism",
        "economic_channel",
        "role_interpretation",
        "inspect_next",
    }
    assert trader_payload["changed_inputs"]
    assert trader_payload["role_interpretation"] != risk_payload["role_interpretation"]
