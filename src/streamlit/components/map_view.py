from pathlib import Path
import streamlit as st
from utils.utils import fill_template_vars  # your helper that replaces placeholders

def render_map(cfg, gj) -> None:
    """
    Render the map using a pre-fetched GeoJSON FeatureCollection (gj).
    No DB/HTTP calls happen here.
    """
    # Load assets
    root = Path(__file__).resolve().parents[1]
    html_path = root / "components" / "html" / "earthquakes.html"
    css_path  = root / "components" / "html" / "earthquakes.css"
    js_path   = root / "components" / "html" / "earthquakes.js"

    html = html_path.read_text(encoding="utf-8")
    css  = css_path.read_text(encoding="utf-8")
    js   = js_path.read_text(encoding="utf-8")

    # Inline-only mode: pass gj directly; leave endpoint empty
    data_endpoint = ""
    inline_geojson = gj or {"type": "FeatureCollection", "features": []}

    # Fill placeholders for BOTH JS and HTML
    js   = fill_template_vars(js,   cfg, data_endpoint, inline_geojson)
    html = fill_template_vars(html, cfg, data_endpoint, inline_geojson)

    # Inline CSS + JS into the HTML template
    html_inlined = (
        html.replace("</head>", f"<style>{css}</style></head>")
        .replace("</body>", f"<script>{js}</script></body>")
    )

    st.components.v1.html(html_inlined, height=780, scrolling=False)
