"""
Main Streamlit Dashboard Entry Point.
Enterprise Multi-Page Analytics Application with URL-based routing via st.navigation().
Pages are accessible at:
  /            → Dashboard Overview
  /forecasting → Energy Demand Forecasting
  /scheduling  → Machine Job Scheduling
  /analytics   → Machine Resource Analytics
  /kpi         → Performance KPI Metrics
  /comparison  → Schedule Comparison Analysis
  /reports     → Technical Reports Viewer
  /settings    → Settings & Export Center
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
from dashboard.pages.machine_analytics import render_machine_analytics_page
from dashboard.pages.kpi import render_kpi_page
from dashboard.pages.comparison import render_comparison_page
from dashboard.pages.reports import render_reports_page
from dashboard.pages.settings import render_settings_page


# ---------------------------------------------------------------------------
# Shared data loading (cached) — runs once, shared across all page functions
# ---------------------------------------------------------------------------

def _load_all_data():
    """Load all CSV output artefacts with Streamlit caching."""
    pred_df, fut_df = load_predictions_data()
    opt_df, fcfs_df, kpi_df, comp_df = load_scheduling_data()
    jobs_df, machines_df = load_job_and_machine_data()
    return pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df


# ---------------------------------------------------------------------------
# Page builder helpers — each wrapped in a lambda so st.Page can call them
# ---------------------------------------------------------------------------

def _build_page_home():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_home_page(
        opt_df=opt_df,
        fcfs_df=fcfs_df,
        kpi_df=kpi_df,
        jobs_df=jobs_df,
        machines_df=machines_df,
        pred_df=pred_df,
    )


def _build_page_forecasting():
    pred_df, fut_df, *_ = _load_all_data()
    _, _, _, _, _, _, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_forecasting_page(pred_df=pred_df, fut_df=fut_df)


def _build_page_scheduling():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_scheduling_page(opt_df=opt_df, filters=filters)


def _build_page_analytics():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_machine_analytics_page(opt_df=opt_df, machines_df=machines_df, filters=filters)


def _build_page_kpi():
    _, _, _, _, kpi_df, _, _, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_kpi_page(kpi_df=kpi_df)


def _build_page_comparison():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_comparison_page(opt_df=opt_df, fcfs_df=fcfs_df, kpi_df=kpi_df, comp_df=comp_df)


def _build_page_reports():
    _, _, _, _, _, _, _, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_reports_page()


def _build_page_settings():
    pred_df, fut_df, opt_df, fcfs_df, kpi_df, comp_df, jobs_df, machines_df = _load_all_data()
    available_machines = (
        machines_df["Machine_ID"].tolist()
        if not machines_df.empty and "Machine_ID" in machines_df.columns
        else [f"M{i}" for i in range(1, 11)]
    )
    filters = render_sidebar(available_machines=available_machines)
    render_settings_page(opt_df=opt_df, fcfs_df=fcfs_df, kpi_df=kpi_df, pred_df=pred_df)


# ---------------------------------------------------------------------------
# Application entry point — uses st.navigation() for real URL routing
# ---------------------------------------------------------------------------

def main():
    """Streamlit Application Main Execution Routine with URL-based page routing."""
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

    # Render Top Navigation Header Bar
    render_navbar(system_status="SYSTEM OPERATIONAL")

    # Define pages with URL-slug, title, and icon
    # URL slugs determine the browser address: /forecasting, /scheduling, etc.
    pages = [
        st.Page(_build_page_home,        title="Dashboard Overview",          icon="🏭", url_path="home",        default=True),
        st.Page(_build_page_forecasting, title="Energy Demand Forecasting",   icon="📈", url_path="forecasting"),
        st.Page(_build_page_scheduling,  title="Machine Job Scheduling",      icon="📋", url_path="scheduling"),
        st.Page(_build_page_analytics,   title="Machine Resource Analytics",  icon="⚙️",  url_path="analytics"),
        st.Page(_build_page_kpi,         title="Performance KPI Metrics",     icon="📊", url_path="kpi"),
        st.Page(_build_page_comparison,  title="Schedule Comparison Analysis",icon="🔍", url_path="comparison"),
        st.Page(_build_page_reports,     title="Technical Reports Viewer",    icon="📄", url_path="reports"),
        st.Page(_build_page_settings,    title="Settings & Export Center",    icon="⚙️",  url_path="settings"),
    ]

    # st.navigation renders the sidebar nav automatically and returns the active page
    pg = st.navigation(pages, position="hidden")  # position="hidden" because sidebar.py renders its own filter controls
    pg.run()


if __name__ == "__main__":
    main()
