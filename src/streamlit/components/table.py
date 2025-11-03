from utils.utils import features_to_dataframe
import streamlit as st
from typing import Dict, Any
import math

VISIBLE_COLS = ["time", "mag", "depth_km", "lon", "lat", "place", "tsunami"]

def render_table(gj: Dict[str, Any]) -> None:
    """
    Render the earthquake table from a pre-fetched GeoJSON FeatureCollection (gj).
    - Page size choices: 10, 20, 50, or 'Show all'
    - By default, displays only selected columns (others are still present in df).
    - Toggle lets users see all columns without re-fetching.
    """
    # Show how many earthquake events matched the current filters
    count = len((gj or {}).get("features", []) or [])
    label = "earthquake" if count == 1 else "earthquakes"
    st.info(f"**{count:,} {label}** matched the current filters.")

    try:
        df = features_to_dataframe(gj)
        if df.empty:
            st.caption("No results to display.")
            return

        if "time" in df.columns:
            df = df.sort_values("time", ascending=True).reset_index(drop=True)

        # ——— Pagination state (read defaults BEFORE slicing) ———
        if "pag_page" not in st.session_state:
            st.session_state.pag_page = 1
        if "pag_size" not in st.session_state:
            st.session_state.pag_size = 10
        if "pag_size_prev" not in st.session_state:
            st.session_state.pag_size_prev = st.session_state.pag_size
        if "pag_count_last" not in st.session_state:
            st.session_state.pag_count_last = count

        # Reset page if result count changed (e.g., filters updated)
        if st.session_state.pag_count_last != count:
            st.session_state.pag_page = 1
            st.session_state.pag_count_last = count

        # Handle "Show all" case
        page_size = st.session_state.pag_size
        show_all_rows = page_size == "Show all"

        if show_all_rows:
            total_pages = 1
            start, end = 0, count
        else:
            total_pages = max(1, math.ceil(count / page_size))
            st.session_state.pag_page = max(1, min(st.session_state.pag_page, total_pages))
            start = (st.session_state.pag_page - 1) * page_size
            end = start + page_size

        df_view = df.iloc[start:end].copy()

        # Table + range caption (controls will be rendered below)
        if show_all_rows:
            st.caption(f"Showing all **{count}** {label}.")
        else:
            st.caption(f"Showing rows **{start + 1}–{min(end, count)}** of **{count}**.")

        show_all_cols = st.toggle("Show all columns", value=False)

        if show_all_cols:
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            cols_in_df = [c for c in VISIBLE_COLS if c in df_view.columns]
            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_order=cols_in_df,
            )

        render_pagination(total_pages, show_all_rows)

    except Exception as e:
        st.error(f"Failed to render earthquake table: {e}")


def render_pagination(total_pages: int, show_all_rows: bool):
    # Set column ratio
    c_size, c_info, c_first, c_prev, c_next, c_last = st.columns([0.9, 2.0, 1.0, 1.0, 1.0, 1.0])

    with c_size:
        # Add "Show all" option
        options = [10, 20, 50, "Show all"]
        current_value = st.session_state.pag_size

        st.selectbox(
            "Rows/page",
            options=options,
            index=options.index(current_value) if current_value in options else 0,
            key="pag_size",
            label_visibility="collapsed",
            help="Rows per page",
        )
        # If page size changed, reset to page 1 and rerun so slice updates immediately
        if st.session_state.pag_size != st.session_state.pag_size_prev:
            st.session_state.pag_size_prev = st.session_state.pag_size
            st.session_state.pag_page = 1
            st.rerun()

    with c_info:
        if show_all_rows:
            st.markdown(f"**Showing all results**")
        else:
            st.markdown(f"**Page {st.session_state.pag_page} of {total_pages}**")

    # Disable buttons if "Show all" is active
    disabled = show_all_rows or total_pages <= 1

    with c_first:
        if st.button("⏮ First", use_container_width=True, disabled=disabled or st.session_state.pag_page == 1):
            st.session_state.pag_page = 1
            st.rerun()
    with c_prev:
        if st.button("◀ Prev", use_container_width=True, disabled=disabled or st.session_state.pag_page == 1):
            st.session_state.pag_page = max(1, st.session_state.pag_page - 1)
            st.rerun()
    with c_next:
        if st.button("Next ▶", use_container_width=True, disabled=disabled or st.session_state.pag_page >= total_pages):
            st.session_state.pag_page = min(total_pages, st.session_state.pag_page + 1)
            st.rerun()
    with c_last:
        if st.button("Last ⏭", use_container_width=True, disabled=disabled or st.session_state.pag_page >= total_pages):
            st.session_state.pag_page = total_pages
            st.rerun()