"""
Main Streamlit Dashboard Entry Point.
Enterprise Streamlined Multi-Page Analytics Application with URL-based routing via st.navigation().

Simplified Page Navigation:
  /home        → Dashboard Overview (default)
  /scheduling  → Machine Job Scheduling & Gantt Timeline
  /forecasting → Energy Demand Forecasting
  /kpi         → Performance KPIs & Benchmark Comparison
  /settings    → Data Export & System Settings
"""

import sys
from pathlib import Path
import streamlit as st

# Add project root to Python module search path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dashboard.components.theme import inject_custom_css
from dashboard.components.navbar import render_navbar
from dashboard.components.sidebar import render_sidebar

from dashboard.utils.loader import (
    load_predictions_data,
    load_scheduling_data,
    load_job_and_machine_data,
)

from dashboard.pages.home import render_home_page
from dashboard.pages.forecasting import render_forecasting_page
from dashboard.pages.scheduling import render_scheduling_page
from dashboard.pages.kpi import render_kpi_page
from dashboard.pages.settings import render_settings_page


# ---------------------------------------------------------------------------
# Shared setup — runs at start of every page
# ---------------------------------------------------------------------------

def _setup():
    """Load all data and sidebar filters."""
    pred_df, fut_df = load_predictions_data()
    opt_df, fcfs_df, kpi_df, comp_df = load_scheduling_data()
    jobs_df, machines_df = load_job_and_machine_data()

    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )

    filters = render_sidebar(available_machines=available_machines)

    return pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters


# ---------------------------------------------------------------------------
# Individual page functions — called by st.navigation()
# ---------------------------------------------------------------------------

def page_home():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters = _setup()
    render_home_page(opt_df=opt_df, fcfs_df=fcfs_df, kpi_df=kpi_df,
                     jobs_df=jobs_df, machines_df=machines_df, pred_df=pred_df)


def page_scheduling():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters = _setup()
    render_scheduling_page(opt_df=opt_df, filters=filters)


def page_forecasting():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters = _setup()
    render_forecasting_page(pred_df=pred_df, fut_df=fut_df)


def page_kpi():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters = _setup()
    render_kpi_page(kpi_df=kpi_df, opt_df=opt_df, fcfs_df=fcfs_df, comp_df=comp_df)


def page_settings():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df, filters = _setup()
    render_settings_page(opt_df=opt_df, fcfs_df=fcfs_df, kpi_df=kpi_df, pred_df=pred_df)


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

def main():
    """Streamlit Application Main Execution Routine."""
    st.set_page_config(
        page_title="Smart Factory Machine Scheduler & Energy AI",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize Theme Mode State
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Light"

    # Inject Custom Enterprise CSS Theme
    inject_custom_css(theme_mode=st.session_state["theme_mode"])

    # Render Top Navigation Header Bar with Logo and Title
    render_navbar(system_status="SYSTEM OPERATIONAL")

    # Clean, intuitive page list (Technical Reports Viewer removed, navigation simplified)
    pages = [
        st.Page(page_home,        title="Overview",                      icon="🏭", url_path="home", default=True),
        st.Page(page_scheduling,  title="Machine Scheduling",            icon="📋", url_path="scheduling"),
        st.Page(page_forecasting, title="Energy Demand Forecasting",     icon="📈", url_path="forecasting"),
        st.Page(page_kpi,         title="Performance KPIs & Benchmark", icon="📊", url_path="kpi"),
        st.Page(page_settings,    title="Export & Settings",             icon="⚙️", url_path="settings"),
    ]

    pg = st.navigation(pages, position="sidebar")
    pg.run()


if __name__ == "__main__":
    main()
