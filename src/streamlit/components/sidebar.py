from dataclasses import dataclass
from datetime import datetime, date, time as dtime, timezone
import streamlit as st

from data.data_sources import DATA_SOURCES

@dataclass
class AppConfig:
    # data source & tokens
    ds_choice: object
    mapbox_token: str

    # map config
    style_name: str
    style_url: str
    layer_mode: str

    # time range
    start_dt: datetime
    end_dt: datetime

    # filters
    mag_min: float
    mag_max: float
    depth_min: float
    depth_max: float
    tsunami_only: bool
    text_query: str
    networks_csv: str
    bbox: list | None

    # playback
    speed_hps: float

def render_sidebar() -> AppConfig:
    st.sidebar.header("Data & Map")

    st.sidebar.header("Playback")
    speed_multiplier = st.sidebar.slider(
        "Speed (hours/second)",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        format="%dx"
    )
    # JS expects hours/second → treat 1x..10x as 1..10 hours/second
    speed_hps = float(speed_multiplier)

    ds_choice = st.sidebar.selectbox("Data source", DATA_SOURCES, format_func=lambda d: d.name())

    MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "")

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

    layer_mode = st.sidebar.radio("Layer", ["bubbles", "heatmap"], index=0, horizontal=True)

    st.sidebar.header("Time range (UTC)")
    now = datetime.now(timezone.utc)
    default_end = now
    default_start = default_end.replace(hour=0, minute=0, second=0, microsecond=0)

    start_date = st.sidebar.date_input("Start date", value=default_start.date())
    start_time = st.sidebar.time_input("Start time", value=dtime(0, 0, 0))
    end_date = st.sidebar.date_input("End date", value=default_end.date())
    end_time = st.sidebar.time_input("End time", value=dtime(default_end.hour, default_end.minute, 0))

    start_dt = datetime.combine(start_date, start_time).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, end_time).replace(tzinfo=timezone.utc)

    st.sidebar.header("Filters")
    mag_min, mag_max = st.sidebar.slider("Magnitude range", 0.0, 10.0, (0.0, 10.0), 0.1)
    depth_min, depth_max = st.sidebar.slider("Depth range (km)", 0.0, 700.0, (0.0, 700.0), 10.0)
    tsunami_only = st.sidebar.checkbox("Tsunami only", value=False)
    text_query = st.sidebar.text_input("Text search in title/place (contains)", value="")
    networks_csv = st.sidebar.text_input("Restrict to networks (comma-separated, e.g., us,ak,pr)", value="")
    use_bbox = st.sidebar.checkbox("Restrict to bounding box", value=False)

    col1, col2 = st.sidebar.columns(2)
    min_lon = col1.number_input("min lon", value=-180.0, step=0.5, format="%.4f")
    min_lat = col1.number_input("min lat", value=-85.0, step=0.5, format="%.4f")
    max_lon = col2.number_input("max lon", value=180.0, step=0.5, format="%.4f")
    max_lat = col2.number_input("max lat", value=85.0, step=0.5, format="%.4f")
    bbox = [min_lon, min_lat, max_lon, max_lat] if use_bbox else None

    return AppConfig(
        ds_choice=ds_choice,
        mapbox_token=MAPBOX_TOKEN,
        style_name=style_name,
        style_url=style_url,
        layer_mode=layer_mode,
        start_dt=start_dt,
        end_dt=end_dt,
        mag_min=mag_min,
        mag_max=mag_max,
        depth_min=depth_min,
        depth_max=depth_max,
        tsunami_only=tsunami_only,
        text_query=text_query,
        networks_csv=networks_csv,
        bbox=bbox,
        speed_hps=speed_hps,
    )
