from datetime import datetime, timezone
import streamlit as st

from utils.utils import fetch_geojson_for_cfg
from components.sidebar import render_sidebar
from components.map_view import render_map
from components.table import render_table
from components.histograms import render_mag_hist, render_depth_hist

st.set_page_config(page_title="Earthquakes — JS in Streamlit (Pro)", layout="wide")

# Sidebar → collect all inputs/config in one place
cfg = render_sidebar()

# Guard on invalid range
if cfg.start_dt >= cfg.end_dt:
    st.sidebar.error("Start must be before end. Showing nothing until fixed.")
    st.stop()


try:
    # --------------------------------------------------------------------
    # Fetch data ONCE (DB via ORM if available; else HTTP), then pass `gj`
    # --------------------------------------------------------------------
    gj = fetch_geojson_for_cfg(cfg)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# --------------------
# Render UI components
# --------------------
render_map(cfg, gj)

st.subheader("Event Data Table")
render_table(gj)

st.subheader("Distributions")
render_mag_hist(gj)
render_depth_hist(gj)
