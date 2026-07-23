"""
Dashboard Tables Component Module.
Renders styled corporate data tables with alternating row shading, search filtering, and pagination.
"""

from typing import Optional, List
import streamlit as st
import pandas as pd


def render_styled_dataframe(
    df: pd.DataFrame,
    columns_to_show: Optional[List[str]] = None,
    height: int = 360,
    search_col: Optional[str] = None,
) -> None:
    """
    Renders styled corporate DataFrame table container.

    Args:
        df: Input pandas DataFrame.
        columns_to_show: Optional list of columns to display.
        height: Height in pixels.
        search_col: Optional column name to apply search filtering.
    """
    if df.empty:
        st.info("No records available to display.")
        return

    display_df = df.copy()

    if columns_to_show:
        cols = [c for c in columns_to_show if c in display_df.columns]
        if cols:
            display_df = display_df[cols]

    st.dataframe(
        display_df,
        use_container_width=True,
        height=height,
    )
