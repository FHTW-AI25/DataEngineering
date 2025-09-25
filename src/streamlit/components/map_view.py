from pathlib import Path
import streamlit as st

from utils import js_bool, js_str

def render_map(cfg) -> None:
    # Load assets
    root = Path(__file__).resolve().parents[1]
    html_path = root / "components" / "html" / "earthquakes.html"
    css_path  = root / "components" / "html" / "earthquakes.css"
    js_path   = root / "components" / "html" / "earthquakes.js"

    html = html_path.read_text(encoding="utf-8")
    css  = css_path.read_text(encoding="utf-8")
    js   = js_path.read_text(encoding="utf-8")

    # Fill template vars in JS
    js = (
        js
        .replace("__MAPBOX_TOKEN__", js_str(cfg.mapbox_token))
        .replace("__MAP_STYLE__", js_str(cfg.style_url))
        .replace("__MAP_STYLE_NAME__", js_str(cfg.style_name))
        .replace("__LAYER_MODE__", js_str(cfg.layer_mode))
        .replace("__SPEED_HPS__", str(cfg.speed_hps))
        .replace("__START_MS__", str(int(cfg.start_dt.timestamp() * 1000)))
        .replace("__END_MS__", str(int(cfg.end_dt.timestamp() * 1000)))
        .replace("__MAG_MIN__", str(cfg.mag_min))
        .replace("__MAG_MAX__", str(cfg.mag_max))
        .replace("__DEPTH_MIN__", str(cfg.depth_min))
        .replace("__DEPTH_MAX__", str(cfg.depth_max))
        .replace("__TSUNAMI_ONLY__", js_bool(cfg.tsunami_only))
        .replace("__TEXT_QUERY__", js_str(cfg.text_query.strip().lower()))
        .replace("__NETWORKS_JSON__", str([s.strip().lower() for s in cfg.networks_csv.split(",") if s.strip()]))
        .replace("__BBOX_JSON__", "null" if cfg.bbox is None else str(cfg.bbox))
        .replace("__DATA_ENDPOINT__", js_str(cfg.ds_choice.get_endpoint(
            start_ms=int(cfg.start_dt.timestamp()*1000),
            end_ms=int(cfg.end_dt.timestamp()*1000),
        )))
        .replace("__START_ISO__", cfg.start_dt.isoformat().replace("T"," ").replace("+00:00"," Z"))
        .replace("__END_ISO__", cfg.end_dt.isoformat().replace("T"," ").replace("+00:00"," Z"))
    )

    # Inline CSS + JS into the HTML template
    html_inlined = (
        html.replace("</head>", f"<style>{css}</style></head>")
        .replace("</body>", f"<script>{js}</script></body>")
    )

    st.components.v1.html(html_inlined, height=780, scrolling=False)
