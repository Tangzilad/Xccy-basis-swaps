from __future__ import annotations

import streamlit as st

from src.controllers.market_state_controller import make_stress_table
from src.state.session_access import get_canonical_market_context
from src.controllers.market_state_controller import make_stress_table, summarize_for_shell
from ui_shell import LEARNING_PATH, ensure_market_state_initialized, learning_hint, render_global_shell

st.set_page_config(page_title="XCCY Basis Learning Lab", page_icon="📘", layout="wide")
ensure_market_state_initialized()
render_global_shell()
st.session_state.suggested_page = LEARNING_PATH[0]

context = get_canonical_market_context(st.session_state)
state = context["state"]
summary = context["summary_1y"]["base"]
market_state = st.session_state["market_state"]
base_snapshot = market_state["base_snapshot"]
stressed_snapshot = market_state["stressed_snapshot"]
state_snapshot = {"mode": st.session_state.get("mode", "Basic"), **summarize_for_shell(base_snapshot)}

st.title("XCCY Basis Learning Lab")
st.caption("A guided multipage walkthrough from foundations to strategy stress testing.")

st.markdown("## 1. Start here")
summary_col, status_col = st.columns([2, 1])
with summary_col:
    st.write(
        "Use the sidebar controls to set a shared canonical market state. Then move through pages in order to build "
        "intuition from mechanics to implementation."
    )
with status_col:
    st.metric("Mode", str(st.session_state.get("mode", "Basic")))
    st.metric("Basis (1Y)", f"{summary['basis_bps']:.0f} bps")

st.markdown("### Suggested learning path")
for step in LEARNING_PATH:
    st.write(step)

learning_hint(
    "In Learning mode, each page highlights why the metric matters, what changes with regime shifts, and where model "
    "risk enters decision-making."
)

st.markdown("### Base vs stressed snapshots")
base_snapshot = state["base_snapshot"]
stressed_snapshot = state["stressed_snapshot"]

c1, c2, c3 = st.columns(3)
c1.metric("Scenario", state.get("scenario", "none"))
c1, c2, c3 = st.columns(3)
c1.metric("Scenario", market_state.get("scenario", "none"))
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
