from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    pickup = frame.iloc[-1]["Carry differential (%)"] + frame.iloc[-1]["Basis (bps)"] / 100
    return (
        f"Indicative long-tenor hedged pickup is {pickup:.2f}% after basis adjustment. "
        "Hedge instrument selection should trade off rollover risk, liquidity, and accounting treatment."
    )


render_lesson(
    step_index=5,
    title="6. Hedged pickup and hedge choice",
    summary="Compare all-in pickup under forwards vs cross-currency swaps and relate it to hedge design choices.",
    metric_defs=[
        ("All-in pickup", "basis-adjusted", "instrument-sensitive"),
        ("Rollover risk", "path-dependent", "hedge-horizon linked"),
        ("Liquidity cost", "market-state linked", "execution-dependent"),
    ],
    explanation_fn=explain,
    theory_text="The best hedge is not always the highest-carry one; governance, liquidity, and accounting outcomes matter.",
    calc_text="Pickup shown here combines carry differential with basis converted from bps to percentage points.",
)
