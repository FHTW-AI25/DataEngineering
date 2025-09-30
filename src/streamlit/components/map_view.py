from pathlib import Path
import streamlit as st
from utils.utils import fill_template_vars

def render_map(cfg) -> None:
    # Load assets
    root = Path(__file__).resolve().parents[1]
    html_path = root / "components" / "html" / "earthquakes.html"
    css_path  = root / "components" / "html" / "earthquakes.css"
    js_path   = root / "components" / "html" / "earthquakes.js"

    html = html_path.read_text(encoding="utf-8")
    css  = css_path.read_text(encoding="utf-8")
    js   = js_path.read_text(encoding="utf-8")

    # If this data source can fetch inline GeoJSON (ORM/DB), use it; else we’ll fetch via DATA_ENDPOINT.
    # ToDo Sebastian adapt this here to only use db as datasource
    inline_geojson = None
    if hasattr(cfg.ds_choice, "fetch_geojson"):
        try:
            # fetch data from custom db
            inline_geojson = cfg.ds_choice.fetch_geojson(
                start_ms=int(cfg.start_dt.timestamp() * 1000),
                end_ms=int(cfg.end_dt.timestamp() * 1000),
                mag_min=cfg.mag_min,
                mag_max=cfg.mag_max,
                depth_min=cfg.depth_min,
                depth_max=cfg.depth_max,
                tsunami_only=cfg.tsunami_only,
                text_query=cfg.text_query,
                networks=[s.strip() for s in cfg.networks_csv.split(",") if s.strip()],
                bbox=cfg.bbox,
            )
        except Exception as e:
            # Fall back to endpoint if DB fetch fails
            st.warning(f"DB inline fetch failed, falling back to HTTP endpoint: {e}")
            inline_geojson = None

    # Build DATA_ENDPOINT only if we are not using inline data
    data_endpoint = ""
    if inline_geojson is None:
        data_endpoint = cfg.ds_choice.get_endpoint(
            start_ms=int(cfg.start_dt.timestamp() * 1000),
            end_ms=int(cfg.end_dt.timestamp() * 1000),
        ) or ""

    js = fill_template_vars(js, cfg, data_endpoint, inline_geojson)
    html = fill_template_vars(html, cfg, data_endpoint, inline_geojson)


    # Inline CSS + JS into the HTML template
    html_inlined = (
        html.replace("</head>", f"<style>{css}</style></head>")
        .replace("</body>", f"<script>{js}</script></body>")
    )

    st.components.v1.html(html_inlined, height=780, scrolling=False)
