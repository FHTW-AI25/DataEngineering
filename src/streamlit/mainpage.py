import streamlit as st

from earthquakes_common import get_session
from utils.utils import fetch_geojson_for_cfg
from components.sidebar import render_sidebar_return_config
from components.map_view import render_map
from components.table import render_table
from components.histograms import render_mag_hist, render_depth_hist

st.set_page_config(page_title="Earthquakes", layout="wide")

# Sidebar -> render sidebar and get config
config = render_sidebar_return_config()

# Guard on invalid date range
if config.start_dt >= config.end_dt:
    st.sidebar.error("Start must be before end. Showing nothing until fixed.")
    st.stop()

#
# Fetch geojson for map/table (from DB if available, else HTTP fallback)
#
try:
    geojson = fetch_geojson_for_cfg(config)
except Exception as e:
    st.error(f"Failed to load quake data: {e}")
    st.stop()

# --------------------
# Render UI components
# --------------------
render_map(config, geojson)

st.subheader("Event Data Table")
render_table(geojson)

st.subheader("Distributions")
render_mag_hist(geojson)
render_depth_hist(geojson)
