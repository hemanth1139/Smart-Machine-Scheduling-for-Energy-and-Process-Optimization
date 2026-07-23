"""
Enterprise Navigation Bar Component Module.
Renders enterprise top header, system health status indicator, and workspace title with logo.
"""

import streamlit as st


def render_navbar(system_status: str = "SYSTEM OPERATIONAL") -> None:
    """
    Renders top navigation header bar with plant logo, title, and live status badge.

    Args:
        system_status: Status text headline.
    """
    html_code = f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.5rem;
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
        color: #FFFFFF;
    ">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="
                background: rgba(37, 99, 235, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.4);
                padding: 0.6rem;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2z"></path>
                    <path d="M17 18h1"></path>
                    <path d="M12 18h1"></path>
                    <path d="M7 18h1"></path>
                </svg>
            </div>
            <div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.01em;">
                    AI Smart Machine Scheduler & Energy Optimizer
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 500; margin-top: 2px;">
                    Industrial AI Decision Support System | UCI Steel Load Optimization
                </div>
            </div>
        </div>
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            background-color: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        ">
            <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #22C55E;"></span>
            <span>{system_status}</span>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)
