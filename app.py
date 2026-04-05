from __future__ import annotations

import streamlit as st

from src.state.market_state import snapshot_for_narrative
from ui_shell import LEARNING_PATH, ensure_market_state_initialized, learning_hint, render_global_shell

st.set_page_config(page_title="XCCY Basis Learning Lab", page_icon="📘", layout="wide")
ensure_market_state_initialized()
render_global_shell()
st.session_state.suggested_page = LEARNING_PATH[0]

state_snapshot = snapshot_for_narrative(st.session_state["market_state"])

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
    st.metric("Mode", str(state_snapshot["mode"]))
    st.metric("Basis", f"{state_snapshot['cross_currency_basis_bps']:.0f} bps")

st.markdown("### Suggested learning path")
for step in LEARNING_PATH:
    st.write(step)

learning_hint(
    "In Learning mode, each page highlights why the metric matters, what changes with regime shifts, and where model "
    "risk enters decision-making."
)

with st.expander("How to navigate"):
    st.write(
        "Proceed page-by-page using Streamlit's left navigation. The same market-state controls stay available across "
        "pages through session state."
    )
