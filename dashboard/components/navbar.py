"""
Enterprise Navigation Bar Component Module.
Renders enterprise top header, system health status indicator, and workspace title.
"""

import streamlit as st


def render_navbar(system_status: str = "SYSTEM OPERATIONAL") -> None:
    """
    Renders top navigation header bar with plant title and live status badge.

    Args:
        system_status: Status text headline.
    """
    html_code = f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.25rem;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05);
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                <line x1="6" y1="6" x2="6.01" y2="6"></line>
                <line x1="6" y1="18" x2="6.01" y2="18"></line>
            </svg>
            <div>
                <div style="font-size: 1.125rem; font-weight: 700; color: #0F172A; line-height: 1.2;">
                    AI Smart Machine Scheduling & Energy Optimization Platform
                </div>
                <div style="font-size: 0.75rem; color: #64748B; font-weight: 500;">
                    Industrial Enterprise Edition | UCI Steel Industry Energy Load
                </div>
            </div>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span>{system_status}</span>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)
