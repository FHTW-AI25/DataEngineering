from datetime import datetime
import requests
import pandas as pd
import streamlit as st

def render_table(cfg) -> None:
    try:
        resp = requests.get(
            cfg.ds_choice.get_endpoint(
                start_ms=int(cfg.start_dt.timestamp() * 1000),
                end_ms=int(cfg.end_dt.timestamp() * 1000),
            ),
            timeout=15,
        )
        resp.raise_for_status()
        gj = resp.json()
        feats = gj.get("features", [])
        rows = []
        for f in feats:
            p = f.get("properties", {})
            g = f.get("geometry", {})
            coords = g.get("coordinates", [None, None, None])
            rows.append({
                "time": datetime.utcfromtimestamp(p.get("time", 0)/1000).strftime("%Y-%m-%d %H:%M:%S"),
                "mag": p.get("mag"),
                "place": p.get("place"),
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
