"""
Enterprise Metric Cards Component Module.
Renders clean, styled card containers with rounded corners, soft shadows, typography, and trend badges.
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
    Renders an enterprise styled metric card container.

    Args:
        title: Card header label string.
        value: Primary metric display value.
        delta: Optional trend indicator string (e.g. "+25.2% Cost Reduction").
        delta_is_positive: If True, renders green success background for delta; else red.
        icon_svg: Optional raw SVG icon code string.
        help_text: Optional tooltip help text.
    """
    delta_html = ""
    if delta:
        badge_class = "kpi-delta-positive" if delta_is_positive else "kpi-delta-negative"
        arrow = "↑" if delta_is_positive else "↓"
        delta_html = f'<div class="kpi-delta {badge_class}">{arrow} {delta}</div>'

    default_icon = """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
    </svg>
    """
    icon_html = icon_svg if icon_svg else default_icon

    card_html = f"""
    <div class="kpi-card">
        <div class="kpi-title">
            {icon_html}
            <span>{title}</span>
        </div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
