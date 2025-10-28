import streamlit as st
from sqlalchemy import text

from location.country_sea_manager import CountrySeaManager
from location.data_loader import DataLoader
from location.location_manager import LocationManager
from data.db import get_session
from quake.quake_loader import load_last_30_days
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
# 1. Make sure we have quake data in the DB
#
with get_session() as s:
    quake_count = s.exec(text("SELECT COUNT(*) FROM quake")).scalar_one()

if quake_count == 0:
    with st.spinner("Loading earthquake data for the last 30 days..."):
        load_last_30_days()

#
# 2. Fill lookup tables (country, sea) and enrich quake locations
#
try:
    data_loader = DataLoader()

    country_sea_manager = CountrySeaManager(data_loader)
    country_sea_manager.fill_all()

    location_manager = LocationManager()
    upserted = location_manager.upsert_locations_for_all_quakes()
    print(f"Upserted {upserted} location rows.")

except Exception as e:
    st.error(f"Failed to prepare location / lookup data: {e}")
    st.stop()

#
# 3. Fetch geojson for map/table (from DB if available, else HTTP fallback)
#
try:
    geojson = fetch_geojson_for_cfg(config)
except Exception as e:
    st.error(f"Failed to load quake data: {e}")
    st.stop()

# --------------------
# 4. Render UI components
# --------------------
render_map(config, geojson)

st.subheader("Event Data Table")
render_table(geojson)

st.subheader("Distributions")
render_mag_hist(geojson)
render_depth_hist(geojson)
