from __future__ import annotations

from page_layout import render_lesson


def explain(frame):
    avg_carry = frame["Carry differential (%)"].mean()
    return (
        f"Average carry differential across tenors is {avg_carry:.2f}%. "
        "Parity gaps emerge when basis and execution costs offset this apparent carry."
    )


render_lesson(
    step_index=2,
    title="3. Parity lab",
    summary="Test covered interest parity with and without basis adjustments under your chosen market state.",
    metric_defs=[
        ("CIP status", "gap-aware", "basis-adjusted"),
        ("Implied fwd bias", "dynamic", "tenor-specific"),
        ("Execution frictions", "non-zero", "desk-dependent"),
    ],
    explanation_fn=explain,
    theory_text="Covered interest parity equates hedged returns, but in practice basis and balance-sheet constraints create wedges.",
    calc_text="Carry differential is simplified as annualized policy-rate spread times maturity fraction.",
)
