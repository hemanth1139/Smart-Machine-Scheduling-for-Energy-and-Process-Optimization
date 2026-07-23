"""
Enterprise Sidebar Filter Component Module.
Renders dataset filter controls (machine selector, priority, search).
Navigation is handled natively by Streamlit st.navigation() in app.py.
"""

from typing import Dict, Any, List
import streamlit as st

from dashboard.utils.logger import dash_logger


def render_sidebar(available_machines: List[str]) -> Dict[str, Any]:
    """
    Renders enterprise Streamlit sidebar filter controls.

    Args:
        available_machines: List of machine IDs available in workspace.

    Returns:
        Dict[str, Any]: Filter parameters dictionary.
    """
    st.sidebar.markdown(
        """
        <div style="padding: 0.5rem 0; margin-bottom: 1rem;">
            <div style="font-size: 1rem; font-weight: 700; color: #2563EB;">Enterprise Industrial AI</div>
            <div style="font-size: 0.75rem; color: #64748B;">Decision Support System</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Global Filters**")

    # Machine Selector
    selected_machines = st.sidebar.multiselect(
        label="Filter Machines",
        options=available_machines,
        default=available_machines[:5] if available_machines else [],
    )

    # Job Priority Selector
    selected_priorities = st.sidebar.multiselect(
        label="Job Priority",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
    )

    # Job Search Text
    search_query = st.sidebar.text_input(
        label="Search Job ID",
        value="",
        placeholder="e.g. J1, J12...",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by XGBoost & OR-Tools CP-SAT")

    filters = {
        "machines": selected_machines,
        "priorities": selected_priorities,
        "search_query": search_query.strip(),
    }

    dash_logger.info(f"Sidebar filter: Machines={len(selected_machines)}, Priorities={selected_priorities}")
    return filters
