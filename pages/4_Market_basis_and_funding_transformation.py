from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    min_basis = frame["Basis (bps)"].min()
    return (
        f"Most negative tenor in this scenario is {min_basis:.1f} bps. "
        "That level signals how expensive it is to transform funding across currencies."
    )


render_lesson(
    step_index=3,
    title="4. Market basis and funding transformation",
    summary="Relate observed basis levels to collateral terms, balance-sheet usage, and funding transformation demand.",
    metric_defs=[
        ("Transformation pressure", "state-linked", "balance-sheet sensitive"),
        ("Collateral impact", "material", "CSA-specific"),
        ("Curve depth", "tenor-varying", "liquidity-driven"),
    ],
    explanation_fn=explain,
    theory_text="Basis often reflects structural demand imbalances between natural borrowers and lenders in each currency.",
    calc_text="Displayed basis path applies regime multiplier to highlight sensitivity under stress.",
)
