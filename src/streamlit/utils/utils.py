import json

def js_bool(b: bool) -> str:
    return "true" if b else "false"

def js_str(s: str) -> str:
    # robust JS string literal (uses Python's repr for basic escaping)
    return repr(s)

def fill_template_vars(template: str, cfg, data_endpoint: str, inline_geojson: dict | None) -> str:
    """
    Replace placeholders in a template string (JS or HTML).

    Args:
        template: the JS/HTML string with placeholders like __MAPBOX_TOKEN__
        cfg: your config object with attributes (mapbox_token, style_url, etc.)
        data_endpoint: string, the HTTP endpoint ("" if not used)
        inline_geojson: dict or None, FeatureCollection from ORM datasource

    Returns:
        str with placeholders replaced.
    """
    return (
        template
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
        .replace(
            "__NETWORKS_JSON__",
            str([s.strip().lower() for s in cfg.networks_csv.split(",") if s.strip()])
        )
        .replace("__BBOX_JSON__", "null" if cfg.bbox is None else str(cfg.bbox))
        .replace("__DATA_ENDPOINT__", js_str(data_endpoint or ""))
        .replace("__USE_INLINE__", "true" if inline_geojson else "false")
        .replace("__INLINE_GEOJSON__", json.dumps(inline_geojson) if inline_geojson else "null")
        .replace("__START_ISO__", cfg.start_dt.isoformat().replace("T", " ").replace("+00:00", " Z"))
        .replace("__END_ISO__", cfg.end_dt.isoformat().replace("T", " ").replace("+00:00", " Z"))
    )