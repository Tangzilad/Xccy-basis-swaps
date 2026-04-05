from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from ui_shell import LEARNING_PATH, learning_hint, render_global_shell


VOL_MULTIPLIER = {"Calm": 0.8, "Normal": 1.0, "Stressed": 1.4}
PAGE_CONTEXT_BY_STEP = {
    1: "mechanics",
    2: "parity",
    3: "funding",
    4: "frictions",
    5: "hedge",
    6: "stress",
}


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
    render_global_shell(page_context=PAGE_CONTEXT_BY_STEP.get(step_index, "overview"))
    st.session_state.suggested_page = LEARNING_PATH[step_index]

    st.title(title)
    st.markdown("### Summary")
    st.write(summary)

    st.markdown("### Metrics")
    metric_cols = st.columns(len(metric_defs))
    for col, (label, value, delta) in zip(metric_cols, metric_defs):
        col.metric(label, value, delta)

    st.markdown("### Chart / table")
    tenors = np.array([1, 3, 6, 12, 24, 60])
    base = st.session_state.base_rate
    quote = st.session_state.quote_rate
    basis_bps = st.session_state.cross_currency_basis_bps
    vol_mul = VOL_MULTIPLIER[st.session_state.vol_regime]

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
    latest_narrative = st.session_state.get("latest_transition_narrative")
    if isinstance(latest_narrative, dict):
        with st.expander("Shared state-transition narrative", expanded=False):
            st.markdown("#### Changed inputs")
            if latest_narrative.get("changed_inputs"):
                for change in latest_narrative["changed_inputs"]:
                    st.write(f"- `{change['name']}`: {change['previous']} → {change['current']}")
            else:
                st.write("- No included inputs changed.")
            st.markdown("#### Transmission mechanism / formula")
            st.write(latest_narrative.get("transmission_mechanism", ""))
            st.markdown("#### Economic channel")
            st.write(latest_narrative.get("economic_channel", ""))
            st.markdown("#### Role interpretation")
            st.write(latest_narrative.get("role_interpretation", ""))
            st.markdown("#### Inspect next")
            st.write(latest_narrative.get("inspect_next", ""))
    learning_hint(
        "Interpretation changes by regime: in stressed markets, basis persistence often dominates simple carry "
        "comparisons."
    )

    with st.expander("Theory"):
        st.write(theory_text)

    with st.expander("Calculation notes"):
        st.write(calc_text)
