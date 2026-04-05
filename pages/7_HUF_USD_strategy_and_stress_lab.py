from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    tail = frame["Basis (bps)"].abs().max()
    return (
        f"Stress sensitivity peaks at about {tail:.1f} bps equivalent in this synthetic setup. "
        "For HUF/USD, scenario design should include liquidity gaps, central-bank path shifts, and basis jump risk."
    )


render_lesson(
    step_index=6,
    title="7. HUF/USD strategy and stress lab",
    summary="Apply the framework to HUF/USD with scenario overlays for rate shocks, basis jumps, and funding volatility.",
    metric_defs=[
        ("Strategy stance", "scenario-tested", "rule-based"),
        ("Tail exposure", "non-linear", "stress-sensitive"),
        ("Hedge robustness", "multi-scenario", "decision-critical"),
    ],
    explanation_fn=explain,
    theory_text="EM currency overlays require explicit liquidity and policy-regime assumptions beyond standard G10 carry logic.",
    calc_text="Stress lab visual remains illustrative; extend by plugging in historical HUF/USD basis and vol observations.",
)
