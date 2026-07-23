"""
Enterprise Sidebar Filter Component Module.
Renders clean dataset filter controls (machine selector, priority, search).
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
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Schedule Filters")

    # Machine Selector — default ALL machines so nothing is hidden on load
    selected_machines = st.sidebar.multiselect(
        label="Filter by Machine",
        options=available_machines,
        default=available_machines,  # show all machines by default
        help="Select which machines to include in schedule views.",
    )

    # Job Priority Selector
    selected_priorities = st.sidebar.multiselect(
        label="Filter by Job Priority",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
        help="Show only jobs matching the selected priority levels.",
    )

    # Job ID Search — partial match (case-insensitive)
    search_query = st.sidebar.text_input(
        label="Search by Job ID",
        value="",
        placeholder="e.g. J1 or J42",
        help="Searches for jobs matching the entered ID.",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("⚡ Powered by XGBoost & OR-Tools CP-SAT")

    filters = {
        "machines": selected_machines,
        "priorities": selected_priorities,
        "search_query": search_query.strip(),
    }

    dash_logger.info(
        f"Sidebar filter: Machines={len(selected_machines)}/{len(available_machines)}, "
        f"Priorities={selected_priorities}, Search='{search_query.strip()}'"
    )
    return filters
