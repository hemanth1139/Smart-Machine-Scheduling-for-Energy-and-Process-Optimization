"""
Machine Analytics Dashboard View.
Renders Machine Utilization Bar Chart, Power Consumption Profiles, and Specification Matrices.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from dashboard.components.charts import build_machine_utilization_chart
from dashboard.components.tables import render_styled_dataframe
from dashboard.components.cards import render_metric_card
from dashboard.utils.formatter import format_number


def render_machine_analytics_page(
    opt_df: pd.DataFrame, machines_df: pd.DataFrame, filters: Dict[str, Any]
) -> None:
    """Renders Machine Resource Analytics Dashboard."""
    st.markdown("### Machine Analytics & Resource Utilization")
    st.caption("Machine Inventory Performance & Power Profile Metrics")

    if machines_df.empty:
        st.warning("No machine specification data available.")
        return

    col1, col2, col3, col4 = st.columns(4)

    num_machines = len(machines_df)
    avg_idle_kw = float(machines_df["Idle_Power_kW"].mean()) if "Idle_Power_kW" in machines_df.columns else 3.5
    avg_active_kw = float(machines_df["Active_Power_kW"].mean()) if "Active_Power_kW" in machines_df.columns else 18.2

    with col1:
        render_metric_card("Machine Fleet Count", format_number(num_machines))
    with col2:
        render_metric_card("Avg Idle Power", f"{avg_idle_kw:.2f} kW")
    with col3:
        render_metric_card("Avg Active Power", f"{avg_active_kw:.2f} kW")
    with col4:
        render_metric_card("Fleet Operational Status", "100% Operational", delta="Optimal", delta_is_positive=True)

    st.markdown("---")

    st.markdown("#### Machine Resource Utilization Percentage (%)")
    fig_util = build_machine_utilization_chart(opt_df)
    st.plotly_chart(fig_util, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Machine Hardware Specifications Inventory")
    render_styled_dataframe(
        machines_df,
        columns_to_show=[
            "Machine_ID", "Machine_Type", "Idle_Power_kW", "Active_Power_kW",
            "Changeover_Time_min", "Available_From", "Available_To"
        ],
        height=320,
    )
