from __future__ import annotations

import streamlit as st

from src.controllers.market_state_controller import make_stress_table, summarize_for_shell
from src.state.session_access import get_canonical_market_context
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

st.title("XCCY Basis Learning Lab")
st.caption("A guided multipage walkthrough from foundations to strategy stress testing.")

st.markdown("---")

# --- Quick market snapshot ---
st.markdown("### Current Market Snapshot")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Mode", str(st.session_state.get("mode", "Basic")))
m2.metric("Basis (1Y)", f"{summary['basis_bps']:.0f} bps")
m3.metric("Base spot", f"{base_snapshot['spot_fx']:.2f}")
m4.metric("Scenario", state.get("scenario", "none"))

# --- Learning path ---
st.markdown("### Learning Path")
st.markdown(
    "Work through the lessons in order. Each page builds on the previous one, "
    "progressing from basic mechanics to full strategy stress testing."
)

for i, step in enumerate(LEARNING_PATH):
    visited = st.session_state.get("visited_pages", set())
    check = " :white_check_mark:" if i in visited else ""
    st.write(f"{step}{check}")

learning_hint(
    "In **Learning mode**, each page includes:\n"
    "- **Learning objectives** at the top so you know what to focus on\n"
    "- **Richer explanations** of why each metric matters\n"
    "- **Key takeaways** summarising the most important insights\n"
    "- **Comprehension checks** to test your understanding\n\n"
    "Switch to **Basic mode** in the sidebar to hide pedagogical content and focus on the analytics."
)

# --- Base vs stressed snapshots ---
st.markdown("### Base vs Stressed Snapshots")
stress_table = make_stress_table(base_snapshot, stressed_snapshot)
st.dataframe(stress_table, use_container_width=True)

lhs, rhs = st.columns(2)
with lhs:
    st.caption("Base market forwards")
    st.dataframe(base_snapshot["market_forward_df"], use_container_width=True)
with rhs:
    st.caption("Stressed market forwards")
    st.dataframe(stressed_snapshot["market_forward_df"], use_container_width=True)

# --- Concept map ---
st.markdown("### How the Lessons Connect")
st.markdown(
    """
```
XCCY Mechanics (cashflows, basis drag)
    |
    v
Parity Lab (CIP, fair forwards, wedges)
    |
    +---> Funding Transformation (direct vs synthetic routes)
    |
    +---> Persistence / XVA (why wedges stick: frictions)
              |
              v
         Hedged Pickup (carry after costs, hedge choice)
              |
              v
         Strategy & Stress Lab (integrate all, stress test)
              |
              v
         Consolidated Dashboard (all outputs in one view)
```
"""
)

with st.expander("How to navigate"):
    st.write(
        "Use Streamlit's left navigation to move between pages. "
        "The same market-state controls stay available across all pages through session state. "
        "Use the sidebar to change scenarios and regenerate markets."
    )
