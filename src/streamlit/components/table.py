from utils.utils import features_to_dataframe
import pandas as pd
import streamlit as st
from typing import Dict, Any

VISIBLE_COLS = ["time", "mag", "depth_km", "lon", "lat", "place", "tsunami"]

def render_table(gj: Dict[str, Any]) -> None:
    """
    Render the eartnquake table from a pre-fetched GeoJSON FeatureCollection (gj).
    - Shows only the first 10 rows.
    - By default, displays only selected columns (others are still present in df).
    - Toggle lets users see all columns without re-fetching.
    """
    # Show how many earthquak events matched the current filters
    count = len((gj or {}).get("features", []) or [])
    label = "earthquake" if count == 1 else "earthquakes"
    st.info(f"**{count:,} {label}** matched the current filters.")

    # Optional: if your table shows only the first 10 rows, note that:
    if count > 10:
        st.caption("Showing the first 10 results below.")
    try:
        df = features_to_dataframe(gj)

        if df.empty:
            return

        # Sort by time (oldest → newest). Flip to descending if preferred.
        if "time" in df.columns:
            df = df.sort_values("time", ascending=True)

        # Only show the first 10 earthquake events
        df_view = df.head(10)

        # Toggle: show all columns vs. default visible columns
        show_all = st.toggle("Show all columns", value=False)

        if show_all:
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            # Keep other columns in df_view but only display selected ones
            cols_in_df = [c for c in VISIBLE_COLS if c in df_view.columns]
            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_order=cols_in_df,  # <- hides others in the UI only
            )

    except Exception as e:
        st.error(f"Failed to render earthquake table: {e}")
