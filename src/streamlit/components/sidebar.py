from __future__ import annotations

import os
from datetime import datetime, time, timezone
from dateutil.relativedelta import relativedelta
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import text
from earthquakes_common import get_session
from utils.types import AppConfig, LocationMode

# Load .env variables (only once)
load_dotenv()

def _fetch_countries_sorted_by_name() -> list[tuple[str, str]]:
    with get_session() as s:
        rows = s.execute(text("SELECT iso, name FROM country ORDER BY name ASC")).fetchall()
    return [(r.iso, r.name) for r in rows]

def render_sidebar_return_config() -> AppConfig:
    # ----------------------------
    # Display options (left here as in your base)
    # ----------------------------
    st.sidebar.header("Display options")

    speed_multiplier = st.sidebar.slider(
        "Playback speed (hours per second)",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        format="%dx"
    )
    # JS expects hours/second -> treat 1x..10x as 1..10 hours/second
    speed_hps = float(speed_multiplier)

    MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

    style_options = {
        "Dark": "mapbox://styles/mapbox/dark-v11",
        "Light": "mapbox://styles/mapbox/light-v11",
        "Streets": "mapbox://styles/mapbox/streets-v12",
        "Outdoors": "mapbox://styles/mapbox/outdoors-v12",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Satellite Streets": "mapbox://styles/mapbox/satellite-streets-v12",
    }
    style_name = st.sidebar.selectbox("Map style", list(style_options.keys()), index=0)
    style_url = style_options[style_name]

    layer_mode = st.sidebar.radio("Layer", ["Bubbles", "Heatmap"], index=0, horizontal=True)

    st.sidebar.divider()

    st.sidebar.header("Filter criteria")

    # --- compact time range row (no separate header) ---
    now_utc = datetime.now(timezone.utc)
    this_month_start_utc = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc)
    default_start_dt_utc = this_month_start_utc - relativedelta(months=1)
    default_end_dt_utc   = now_utc

    cdate1, cdate2 = st.sidebar.columns(2)
    start_date = cdate1.date_input("Start (UTC)", value=default_start_dt_utc.date())
    end_date   = cdate2.date_input("End (UTC)",   value=default_end_dt_utc.date())
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt   = datetime.combine(end_date,   time.max, tzinfo=timezone.utc)

    # Location filter
    loc_choice = st.sidebar.radio(
        "Location", options=["Both", "Land", "Sea"], index=0, horizontal=True,
    )
    location_mode: LocationMode = loc_choice.lower()  # type: ignore

    # --- Countries filter: checkbox + multiselect (no buttons; default empty) ---
    iso_name = _fetch_countries_sorted_by_name()  # [(iso, name)] sorted by name
    names = [name for _, name in iso_name]
    name_to_iso = {name: iso for iso, name in iso_name}

    filter_by_country = st.sidebar.checkbox("Filter by country", value=False)

    selected_names = st.sidebar.multiselect(
        "Countries",
        options=names,
        default=[],                          # default: empty
        disabled=not filter_by_country,      # only active when enabled
        help="When enabled: empty = country_iso IS NULL; non-empty = country_iso IN (selected).",
        key="country_multiselect_names",
        placeholder="No country selected",
    )
    # Convert selection → ISO list (may be empty)
    country_isos = [name_to_iso[n] for n in selected_names] if filter_by_country else []

    # Magnitude / depth
    mag_min, mag_max = st.sidebar.slider("Magnitude", 0.0, 10.0, (0.0, 10.0), 0.1)
    depth_min, depth_max = st.sidebar.slider("Depth (km)", 0.0, 1000.0, (0.0, 1000.0), 10.0)

    tsunami_only = st.sidebar.checkbox("Tsunami only", value=False)

    # Bounding box (optional)
    use_bbox = st.sidebar.checkbox("Restrict to bounding box", value=False)
    col1, col2 = st.sidebar.columns(2)
    min_lon = col1.number_input("min lon", value=-180.0, step=0.5, format="%.4f")
    min_lat = col1.number_input("min lat", value=-85.0, step=0.5, format="%.4f")
    max_lon = col2.number_input("max lon", value=180.0, step=0.5, format="%.4f")
    max_lat = col2.number_input("max lat", value=85.0, step=0.5, format="%.4f")
    bbox = [min_lon, min_lat, max_lon, max_lat] if use_bbox else None

    # Text search LAST, under bbox
    text_query = st.sidebar.text_input("Text search (title/place contains)", value="")

    return AppConfig(
        # playback & map fields (these can still be overridden by a toolbar if you add one)
        speed_hps=speed_hps,
        mapbox_token=MAPBOX_TOKEN,
        style_name=style_name,
        style_url=style_url,
        layer_mode=layer_mode,

        # time & filters
        start_dt=start_dt, end_dt=end_dt,
        location_mode=location_mode,

        # NEW: explicit country filtering contract
        filter_by_country=filter_by_country,   # bool flag
        country_isos=country_isos,             # may be empty

        mag_min=mag_min, mag_max=mag_max,
        depth_min=depth_min, depth_max=depth_max,
        tsunami_only=tsunami_only,
        text_query=text_query,
        networks_csv="",         # removed from UI; left empty
        bbox=bbox,
    )
