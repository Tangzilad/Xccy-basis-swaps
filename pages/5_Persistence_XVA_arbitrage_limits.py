from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    persistence_proxy = abs(frame.iloc[2]["Basis (bps)"] - frame.iloc[3]["Basis (bps)"])
    return (
        f"Mid-curve change between 6M and 12M is {persistence_proxy:.1f} bps. "
        "Low decay can indicate persistent constraints where XVA and capital charges cap arbitrage speed."
    )


render_lesson(
    step_index=4,
    title="5. Persistence / XVA / arbitrage limits",
    summary="Understand why visible dislocations can persist when capital, credit, and margin costs absorb theoretical arbitrage.",
    metric_defs=[
        ("Persistence", "non-trivial", "constraint-driven"),
        ("XVA drag", "portfolio-linked", "counterparty-dependent"),
        ("Arb capacity", "finite", "capital-bound"),
    ],
    explanation_fn=explain,
    theory_text="Even when pricing gaps appear attractive, full-stack costs (FVA/CVA/KVA/MVA) can neutralize expected arbitrage PnL.",
    calc_text="Persistence proxy is illustrative, using local slope in the synthetic basis curve.",
)
