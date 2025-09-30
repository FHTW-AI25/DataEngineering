from datetime import datetime, timezone
import streamlit as st

from components.sidebar import render_sidebar
from components.map_view import render_map
from components.table import render_table

st.set_page_config(page_title="Earthquakes — JS in Streamlit (Pro)", layout="wide")

# Sidebar → collect all inputs/config in one place
cfg = render_sidebar()

# Guard on invalid range
# ToDo Sebastian maybe add more guards here
if cfg.start_dt >= cfg.end_dt:
    st.sidebar.error("Start must be before end. Showing nothing until fixed.")
else:
    # Map (JS + CSS inlined into earthquakes.html)
    render_map(cfg)

    st.subheader("Event Data Table")
    render_table(cfg)
