from __future__ import annotations
from typing import Dict, Any
from utils.utils import features_to_dataframe

import streamlit as st
import pandas as pd
import altair as alt


def hist_chart(df: pd.DataFrame, value_col: str, bins: int, x_title: str, log_scale: bool) -> alt.Chart:
    y_scale = alt.Scale(type="log") if log_scale else alt.Scale()
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(value_col, bin=alt.Bin(maxbins=bins), title=x_title),
            y=alt.Y("count()", title="Count", scale=y_scale),
            tooltip=[alt.Tooltip("count()", title="Count")],
        )
        .properties(height=240)
        .interactive()
    )


def render_mag_hist(gj: Dict[str, Any]) -> None:
    """Histogram of magnitude for the provided GeoJSON FeatureCollection."""
    st.subheader("Magnitude distribution")

    try:
        df = features_to_dataframe(gj)
        if not df.empty:
            mag_df = df.dropna(subset=["mag"])
            if mag_df.empty:
                st.info("No magnitude data to plot.")
                return

            c1, c2, c3 = st.columns([1, 1, 2])
            bins = c1.slider("Bins (mag)", 10, 60, 30, 5, key="mag_bins")
            log_y = c2.checkbox("Log scale (Y)", value=False, key="mag_log_y")

            st.altair_chart(hist_chart(mag_df, "mag", bins, "Magnitude", log_y), use_container_width=True)

            with st.expander("Summary stats", expanded=False):
                st.write(mag_df["mag"].describe().to_frame("Magnitudes"))
        else:
            st.info("No events found for selected filters.")
    except Exception as e:
        st.error(f"Failed to render magnitude histogram: {e}")


def render_depth_hist(gj: Dict[str, Any]) -> None:
    """Histogram of depth (km) for the provided GeoJSON FeatureCollection."""
    st.subheader("Depth distribution (km)")

    try:
        df = features_to_dataframe(gj)
        if not df.empty:
            depth_df = df[(df["depth_km"].notna()) & (df["depth_km"] >= 0)]
            if depth_df.empty:
                st.info("No depth data to plot.")
                return

            c1, c2, c3 = st.columns([1, 1, 2])
            bins = c1.slider("Bins (depth)", 10, 80, 40, 5, key="depth_bins")
            log_y = c2.checkbox("Log scale (Y)", value=False, key="depth_log_y")

            st.altair_chart(hist_chart(depth_df, "depth_km", bins, "Depth (km)", log_y), use_container_width=True)

            with st.expander("Summary stats", expanded=False):
                st.write(depth_df["depth_km"].describe().to_frame("Depth (km)"))
        else:
            st.info("No events found for selected filters.")
    except Exception as e:
        st.error(f"Failed to render depth histogram: {e}")
