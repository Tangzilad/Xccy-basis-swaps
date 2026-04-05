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

st.markdown("### Base vs stressed snapshots")
base_snapshot = st.session_state.market_state["base_snapshot"]
stressed_snapshot = st.session_state.market_state["stressed_snapshot"]

c1, c2, c3 = st.columns(3)
c1.metric("Scenario", st.session_state.market_state.get("scenario", "none"))
c2.metric("Base spot", f"{base_snapshot['spot_fx']:.2f}")
c3.metric("Stressed spot", f"{stressed_snapshot['spot_fx']:.2f}")

stress_table = make_stress_table(base_snapshot, stressed_snapshot)
st.dataframe(stress_table, use_container_width=True)

lhs, rhs = st.columns(2)
with lhs:
    st.caption("Base market forwards")
    st.dataframe(base_snapshot["market_forward_df"], use_container_width=True)
with rhs:
    st.caption("Stressed market forwards")
    st.dataframe(stressed_snapshot["market_forward_df"], use_container_width=True)

with st.expander("How to navigate"):
    st.write(
        "Proceed page-by-page using Streamlit's left navigation. The same market-state controls stay available across "
        "pages through session state."
    )
