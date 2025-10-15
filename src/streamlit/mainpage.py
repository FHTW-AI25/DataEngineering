import streamlit as st

from location.country_sea_manager import CountrySeaManager
from location.data_loader import DataLoader
from location.location_manager import LocationManager
from utils.utils import fetch_geojson_for_cfg
from components.sidebar import render_sidebar_return_config
from components.map_view import render_map
from components.table import render_table
from components.histograms import render_mag_hist, render_depth_hist

st.set_page_config(page_title="Earthquakes", layout="wide")

# Sidebar -> render sidebar and get config
cfg = render_sidebar_return_config()

# Guard on invalid date range
if cfg.start_dt >= cfg.end_dt:
    st.sidebar.error("Start must be before end. Showing nothing until fixed.")
    st.stop()


try:
    # --------------------------------------------------------------------
    # Fetch data ONCE (DB via ORM if available; else HTTP)`
    # --------------------------------------------------------------------
    gj = fetch_geojson_for_cfg(cfg)

    data_loader = DataLoader()
    country_sea_manager = CountrySeaManager(data_loader)
    country_sea_manager.ensure_and_fill_all()

    location_manager = LocationManager()
    location_manager.create_table()
    count = location_manager.upsert_locations_for_all_quakes()
    print(f"Upserted {count} location rows.")

except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# --------------------
# Render UI components
# --------------------
render_map(cfg, gj)

st.subheader("Event Data Table")
render_table(gj)

# --- Distribution Components ---
st.subheader("Distributions")
render_mag_hist(gj)
render_depth_hist(gj)
