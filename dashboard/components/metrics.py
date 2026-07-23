"""
Enterprise Grid Metrics Component Module.
Provides helper layouts for rendering 3-column or 4-column metric card grids.
"""

from typing import List, Dict, Any
import streamlit as st
from dashboard.components.cards import render_metric_card


def render_metric_grid(cards_data: List[Dict[str, Any]], num_cols: int = 4) -> None:
    """
    Renders a responsive grid layout of metric cards.

    Args:
        cards_data: List of card specification dicts (title, value, delta, delta_is_positive).
        num_cols: Number of columns in grid (default 4).
    """
    cols = st.columns(num_cols)
    for idx, card in enumerate(cards_data):
        col = cols[idx % num_cols]
        with col:
            render_metric_card(
                title=card.get("title", ""),
                value=card.get("value", ""),
                delta=card.get("delta"),
                delta_is_positive=card.get("delta_is_positive", True),
                icon_svg=card.get("icon_svg"),
            )
