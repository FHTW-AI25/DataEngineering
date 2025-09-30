from utils.utils import features_to_dataframe
import pandas as pd
import streamlit as st
from typing import Dict, Any

def render_table(gj: Dict[str, Any]) -> None:
    """
    Render the events table from a pre-fetched GeoJSON FeatureCollection (gj).
    No DB/HTTP calls happen here.
    """
    try:
        df = features_to_dataframe(gj)

        if not df.empty:
            if "time" in df.columns:
                df = df.sort_values("time", ascending=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No events found for selected filters.")

    except Exception as e:
        st.error(f"Failed to render events table: {e}")
