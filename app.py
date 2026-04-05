from __future__ import annotations

import streamlit as st

from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

st.set_page_config(page_title="XCCY Basis Learning Lab", page_icon="📘", layout="wide")
render_global_shell(page_context="overview")
st.session_state.suggested_page = LEARNING_PATH[0]

st.title("XCCY Basis Learning Lab")
st.caption("A guided multipage walkthrough from foundations to strategy stress testing.")

st.markdown("## 1. Start here")
summary_col, status_col = st.columns([2, 1])
with summary_col:
    st.write(
        "Use the sidebar controls to set a shared market state. Then move through pages in order to build "
        "intuition from mechanics to implementation."
    )
with status_col:
    st.metric("Mode", st.session_state.mode)
    st.metric("Basis", f"{st.session_state.cross_currency_basis_bps} bps")

st.markdown("### Suggested learning path")
for step in LEARNING_PATH:
    st.write(step)

learning_hint(
    "In Learning mode, each page highlights why the metric matters, what changes with regime shifts, and where model "
    "risk enters decision-making."
)

latest_narrative = st.session_state.get("latest_transition_narrative")
if isinstance(latest_narrative, dict):
    st.markdown("### Shared state-transition narrative")
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

with st.expander("How to navigate"):
    st.write(
        "Proceed page-by-page using Streamlit's left navigation. The same market-state controls stay available across "
        "pages through session state."
    )
