import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

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

def features_to_dataframe(gj: Dict[str, Any]) -> pd.DataFrame:
    feats = (gj or {}).get("features", []) or []
    rows: List[Dict[str, Any]] = []
    for f in feats:
        p = f.get("properties", {}) or {}
        g = f.get("geometry", {}) or {}
        coords = g.get("coordinates", [None, None, None]) or [None, None, None]

        time_ms = p.get("time_ms")
        if time_ms is None:
            time_ms = p.get("time")

        time = to_iso(time_ms)

        rows.append({
            "time": time,
            "time_ms": time_ms,
            "mag": p.get("mag"),
            "depth_km": coords[2] if len(coords) > 2 else p.get("depth_km"),
            "lon": coords[0],
            "lat": coords[1],
            "place": p.get("place") or p.get("title"),
            "net": p.get("net"),
            "tsunami": p.get("tsunami"),
            "url": p.get("url"),
        })

    df = pd.DataFrame(rows)
    for col in ["mag", "depth_km", "lon", "lat", "time_ms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "time_ms" in df.columns:
        df["time"] = pd.to_datetime(df["time_ms"], unit="ms", utc=True, errors="coerce")
    return df


def to_iso(ts_ms: int) -> str:
    if not ts_ms and ts_ms != 0:
        return "—"
    # render as UTC
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def fetch_geojson_for_cfg(cfg):
    start_ms = int(cfg.start_dt.timestamp() * 1000)
    end_ms   = int(cfg.end_dt.timestamp() * 1000)

    # Prefer ORM/DB when the datasource provides it
    if hasattr(cfg.ds_choice, "fetch_geojson"):
        return cfg.ds_choice.fetch_geojson(
            start_ms=start_ms,
            end_ms=end_ms,
            mag_min=cfg.mag_min,
            mag_max=cfg.mag_max,
            depth_min=cfg.depth_min,
            depth_max=cfg.depth_max,
            tsunami_only=cfg.tsunami_only,
            text_query=cfg.text_query,
            networks=[s.strip() for s in cfg.networks_csv.split(",") if s.strip()],
            bbox=cfg.bbox,
        )
    # Fallback to HTTP endpoint (e.g., USGS live)
    import requests
    resp = requests.get(
        cfg.ds_choice.get_endpoint(start_ms=start_ms, end_ms=end_ms),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
