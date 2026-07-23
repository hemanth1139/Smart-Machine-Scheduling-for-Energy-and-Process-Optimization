"""
Scheduling Dashboard View.
Renders interactive Plotly Gantt Chart, Machine Timeline, Job Workload Allocation, and Schedule Data Table.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from dashboard.components.charts import (
    build_gantt_chart,
    build_machine_timeline,
    build_job_allocation,
)
from dashboard.components.tables import render_styled_dataframe
from dashboard.components.cards import render_metric_card
from dashboard.utils.formatter import format_currency, format_number


def render_scheduling_page(opt_df: pd.DataFrame, filters: Dict[str, Any]) -> None:
    """Renders Machine Scheduling Dashboard."""
    st.markdown("### Intelligent Machine Scheduling Engine")
    st.caption("Phase 3 Optimization Output (Google OR-Tools CP-SAT Solver)")

    if opt_df.empty:
        st.warning("No schedule output data found. Execute Phase 3 scheduling pipeline first.")
        return

    # Apply Sidebar Filters
    filtered_df = opt_df.copy()
    if filters.get("machines"):
        filtered_df = filtered_df[filtered_df["Assigned_Machine"].isin(filters["machines"])]
    if filters.get("priorities"):
        filtered_df = filtered_df[filtered_df["Priority"].isin(filters["priorities"])]
    if filters.get("search_query"):
        q = filters["search_query"].lower()
        filtered_df = filtered_df[filtered_df["Job_ID"].str.lower().str.contains(q, na=False)]

    # Show filter result count
    total_jobs = len(opt_df)
    shown_jobs = len(filtered_df)
    if shown_jobs < total_jobs:
        st.info(f"🔍 Showing **{shown_jobs}** of **{total_jobs}** jobs — adjust sidebar filters to change the view.")

    if filtered_df.empty:
        st.warning("No jobs match the current filter selection. Clear or adjust the sidebar filters.")
        return

    col1, col2, col3, col4 = st.columns(4)

    scheduled_jobs = len(filtered_df)
    active_machines = filtered_df["Assigned_Machine"].nunique()
    total_cost = float(filtered_df["Energy_Cost_$"].sum()) if "Energy_Cost_$" in filtered_df.columns else 0.0
    late_count = int(filtered_df["Is_Late"].sum()) if "Is_Late" in filtered_df.columns else 0

    with col1:
        render_metric_card("Scheduled Jobs", format_number(scheduled_jobs))
    with col2:
        render_metric_card("Active Machines", format_number(active_machines))
    with col3:
        render_metric_card("Total Energy Cost", format_currency(total_cost))
    with col4:
        render_metric_card(
            "Late Jobs",
            format_number(late_count),
            delta="On Time ✓" if late_count == 0 else f"{late_count} Late",
            delta_is_positive=(late_count == 0),
        )

    st.markdown("---")

    st.markdown("#### Production Job Execution Timeline (Gantt Chart)")
    fig_gantt = build_gantt_chart(filtered_df)
    st.plotly_chart(fig_gantt, use_container_width=True)

    st.markdown("---")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        fig_timeline = build_machine_timeline(filtered_df)
        st.plotly_chart(fig_timeline, use_container_width=True)
    with col_w2:
        fig_alloc = build_job_allocation(filtered_df)
        st.plotly_chart(fig_alloc, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Schedule Assignment Data Table")
    render_styled_dataframe(
        filtered_df,
        columns_to_show=[
            "Job_ID", "Assigned_Machine", "Machine_Type", "Start_Time", "End_Time",
            "Duration_min", "Priority", "Delay_min", "Energy_Cost_$"
        ],
        height=320,
    )
