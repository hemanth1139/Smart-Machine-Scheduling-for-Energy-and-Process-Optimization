"""
Enterprise Metric Cards Component Module.
Uses Streamlit's native st.metric() for reliable rendering across all page contexts,
with custom CSS classes applied via theme.py for visual styling.
"""

from typing import Optional
import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_is_positive: bool = True,
    icon_svg: Optional[str] = None,
    help_text: Optional[str] = None,
) -> None:
    """
    Renders an enterprise styled metric card using st.metric() for cross-context compatibility.

    Args:
        title: Card header label string.
        value: Primary metric display value.
        delta: Optional trend indicator string (e.g. "+25.2% Cost Reduction").
        delta_is_positive: If True, renders green delta colour; else red.
        icon_svg: Optional raw SVG icon (ignored — included for API compatibility).
        help_text: Optional tooltip help text.
    """
    # Build display label — prepend icon emoji placeholder if no svg given
    display_label = title

    # Streamlit st.metric handles delta colour automatically via delta_color param
    if delta is not None:
        # Prefix with +/- sign so Streamlit picks up direction correctly
        delta_display = delta
        delta_color = "normal" if delta_is_positive else "inverse"
        st.metric(
            label=display_label,
            value=value,
            delta=delta_display,
            delta_color=delta_color,
            help=help_text,
        )
    else:
        st.metric(
            label=display_label,
            value=value,
            help=help_text,
        )
