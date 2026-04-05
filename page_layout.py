from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.state.market_state import snapshot_for_narrative
from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


VOL_MULTIPLIER = {"Calm": 0.8, "Normal": 1.0, "Stressed": 1.4}


def render_lesson(
    *,
    step_index: int,
    title: str,
    summary: str,
    metric_defs: list[tuple[str, str, str]],
    explanation_fn,
    theory_text: str,
    calc_text: str,
) -> None:
    st.set_page_config(page_title=title, page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[step_index]

    snapshot = snapshot_for_narrative(st.session_state["market_state"])

    st.title(title)
    st.markdown("### Summary")
    st.write(summary)

    st.markdown("### Metrics")
    metric_cols = st.columns(len(metric_defs))
    for col, (label, value, delta) in zip(metric_cols, metric_defs):
        col.metric(label, value, delta)

    st.markdown("### Chart / table")
    tenors = np.array([1, 3, 6, 12, 24, 60])
    base = float(snapshot["base_rate"])
    quote = float(snapshot["quote_rate"])
    basis_bps = float(snapshot["cross_currency_basis_bps"])
    vol_mul = VOL_MULTIPLIER[str(snapshot["vol_regime"])]

    curve = basis_bps * np.exp(-tenors / 36) * vol_mul
    carry = (quote - base) * tenors / 12

    frame = pd.DataFrame(
        {
            "Tenor (M)": tenors,
            "Basis (bps)": np.round(curve, 1),
            "Carry differential (%)": np.round(carry, 3),
        }
    )
    st.line_chart(frame.set_index("Tenor (M)")["Basis (bps)"], height=220)
    st.dataframe(frame, use_container_width=True)

    st.markdown("### Dynamic explanation")
    st.write(explanation_fn(frame))
    learning_hint(
        "Interpretation changes by regime: in stressed markets, basis persistence often dominates simple carry "
        "comparisons."
    )

    with st.expander("Theory"):
        st.write(theory_text)

    with st.expander("Calculation notes"):
        st.write(calc_text)
