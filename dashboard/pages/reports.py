"""
Report Viewer Dashboard View.
Renders markdown reports generated across Phase 1, Phase 2, and Phase 3 inside the application.
"""

import streamlit as st
from dashboard.utils.loader import load_markdown_report


def render_reports_page() -> None:
    """Renders System Markdown Reports Viewer Page."""
    st.markdown("### System Markdown Reports Viewer")
    st.caption("Inspect detailed technical documentation and execution summaries")

    report_choice = st.selectbox(
        label="Select Technical Report to Display",
        options=[
            "Phase 5: System Validation Report (final_validation_report.md)",
            "Phase 3: Machine Scheduling Report (scheduling_report.md)",
            "Phase 2: Energy Demand Forecasting Report (forecasting_report.md)",
            "Phase 1: Dataset Summary Report (dataset_summary_report.md)",
            "Phase 1: Data Validation Report (data_validation_report.md)",
        ],
        index=0,
    )

    filename_map = {
        "Phase 5: System Validation Report (final_validation_report.md)": "final_validation_report.md",
        "Phase 3: Machine Scheduling Report (scheduling_report.md)": "scheduling_report.md",
        "Phase 2: Energy Demand Forecasting Report (forecasting_report.md)": "forecasting_report.md",
        "Phase 1: Dataset Summary Report (dataset_summary_report.md)": "dataset_summary_report.md",
        "Phase 1: Data Validation Report (data_validation_report.md)": "data_validation_report.md",
    }

    target_file = filename_map[report_choice]
    report_content = load_markdown_report(target_file)

    st.markdown("---")
    st.markdown(report_content)
