"""
Enterprise UI Design System & Theme Engine.
Provides Light/Dark CSS theme styling, Google Fonts (Inter, Roboto), color tokens, and custom container styling.
"""

from typing import Dict, Any
import streamlit as st


def get_theme_colors(theme_mode: str = "Light") -> Dict[str, str]:
    """
    Returns enterprise color palette dictionary for Light or Dark theme mode.

    Args:
        theme_mode: 'Light' or 'Dark'.

    Returns:
        Dict[str, str]: Dictionary of hex color tokens.
    """
    if theme_mode == "Dark":
        return {
            "bg": "#0F172A",
            "card_bg": "#1E293B",
            "card_border": "#334155",
            "text": "#F8FAFC",
            "text_muted": "#94A3B8",
            "primary": "#3B82F6",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "shadow": "0 4px 6px -1px rgba(0,0,0,0.3)",
        }
    return {
        "bg": "#F8FAFC",
        "card_bg": "#FFFFFF",
        "card_border": "#E2E8F0",
        "text": "#0F172A",
        "text_muted": "#64748B",
        "primary": "#2563EB",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "shadow": "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)",
    }


def inject_custom_css(theme_mode: str = "Light") -> None:
    """
    Injects custom enterprise CSS into Streamlit application.

    Args:
        theme_mode: 'Light' or 'Dark'.
    """
    colors = get_theme_colors(theme_mode)

    css_code = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Roboto:wght@400;500;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .stApp {{
        background-color: {colors['bg']};
        color: {colors['text']};
    }}

    /* Main Container Spacing */
    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 95%;
    }}

    /* Enterprise Metric Card Styling */
    .kpi-card {{
        background-color: {colors['card_bg']};
        border: 1px solid {colors['card_border']};
        border-radius: 8px;
        padding: 1.25rem;
        box-shadow: {colors['shadow']};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }}

    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
    }}

    .kpi-title {{
        font-size: 0.875rem;
        font-weight: 500;
        color: {colors['text_muted']};
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .kpi-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {colors['text']};
        letter-spacing: -0.02em;
    }}

    .kpi-delta {{
        font-size: 0.8125rem;
        font-weight: 600;
        margin-top: 0.5rem;
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }}

    .kpi-delta-positive {{
        background-color: rgba(34, 197, 94, 0.15);
        color: #15803D;
    }}

    .kpi-delta-negative {{
        background-color: rgba(239, 68, 68, 0.15);
        color: #B91C1C;
    }}

    /* Status Badge */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8125rem;
        font-weight: 600;
        background-color: rgba(34, 197, 94, 0.15);
        color: #15803D;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }}

    .status-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #22C55E;
    }}

    /* Streamlit Sidebar Customization */
    section[data-testid="stSidebar"] {{
        background-color: {colors['card_bg']};
        border-right: 1px solid {colors['card_border']};
    }}

    /* Streamlit Tabs Customization */
    button[data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 0.9375rem;
        color: {colors['text_muted']};
    }}

    button[aria-selected="true"] {{
        color: {colors['primary']} !important;
        border-bottom-color: {colors['primary']} !important;
    }}
    </style>
    """
    st.markdown(css_code, unsafe_allow_html=True)
