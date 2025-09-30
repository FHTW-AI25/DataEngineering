from datetime import datetime, timezone
import requests
import pandas as pd
import streamlit as st

def _to_iso(ts_ms: int) -> str:
    if not ts_ms:
        return "—"
    # render as UTC
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def render_table(cfg) -> None:
    try:
        # Prefer inline DB fetch if available
        # ToDo Sebastian adapt this here to only use db as datasource
        if hasattr(cfg.ds_choice, "fetch_geojson"):
            gj = cfg.ds_choice.fetch_geojson(
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
        else:
            resp = requests.get(
                cfg.ds_choice.get_endpoint(
                    start_ms=int(cfg.start_dt.timestamp() * 1000),
                    end_ms=int(cfg.end_dt.timestamp() * 1000),
                ),
                timeout=15,
            )
            resp.raise_for_status()
            gj = resp.json()

        feats = (gj or {}).get("features", [])
        rows = []
        for f in feats:
            p = f.get("properties", {}) or {}
            g = f.get("geometry", {}) or {}
            coords = g.get("coordinates", [None, None, None]) or [None, None, None]

            # Normalize time: prefer explicit epoch ms in properties.time or properties.time_ms
            time_ms = p.get("time_ms")
            if time_ms is None:
                time_ms = p.get("time")
            # Fallback: USGS sometimes provides ISO in custom fields (you can extend if needed)

            rows.append({
                "time": _to_iso(int(time_ms)) if isinstance(time_ms, (int, float)) else "—",
                "mag": p.get("mag"),
                "place": p.get("place") or p.get("title"),
                "depth_km": coords[2] if len(coords) > 2 else None,
                "lon": coords[0],
                "lat": coords[1],
                "tsunami": p.get("tsunami"),
                "net": p.get("net"),
                "url": p.get("url"),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No events found for selected filters.")
    except Exception as e:
        st.error(f"Failed to load events for table: {e}")
