from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    near = frame.iloc[0]["Basis (bps)"]
    far = frame.iloc[-1]["Basis (bps)"]
    return (
        f"Short-end basis is {near:.1f} bps while long-end basis is {far:.1f} bps. "
        "This slope helps explain why roll-down can either support or erode realized pickup."
    )


render_lesson(
    step_index=1,
    title="2. XCCY mechanics",
    summary="Map the building blocks: spot, forward points, interest-rate differential, and basis wedge.",
    metric_defs=[
        ("Spot FX", "session", "shared control"),
        ("Basis regime", "term-structured", "observable"),
        ("Funding lens", "secured/unsecured", "choice-dependent"),
    ],
    explanation_fn=explain,
    theory_text="Cross-currency swaps enforce no-arbitrage relationships once funding frictions are accounted for via basis.",
    calc_text="Toy curve uses exponential decay by tenor to keep examples intuitive rather than calibrated to market data.",
)
