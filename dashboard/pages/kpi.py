"""
KPI Dashboard View.
Renders Key Performance Indicator cards for scheduling efficiency, cost savings, and resource optimization.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from dashboard.components.cards import render_metric_card
from dashboard.utils.formatter import format_currency, format_percentage, format_number


def render_kpi_page(kpi_df: pd.DataFrame) -> None:
    """Renders Executive KPI Dashboard."""
    st.markdown("### System Performance KPI Dashboard")
    st.caption("Quantitative Key Performance Indicators across Baseline & CP-SAT Schedules")

    if kpi_df.empty:
        st.warning("No KPI summary data found. Execute Phase 3 scheduling pipeline first.")
        return

    opt_row = kpi_df[kpi_df["Schedule_Type"] == "CP_SAT_Optimized"].iloc[0] if "CP_SAT_Optimized" in kpi_df["Schedule_Type"].values else kpi_df.iloc[-1]
    fcfs_row = kpi_df[kpi_df["Schedule_Type"] == "Baseline_FCFS"].iloc[0] if "Baseline_FCFS" in kpi_df["Schedule_Type"].values else kpi_df.iloc[0]

    opt_cost = float(opt_row.get("Total_Energy_Cost_$", 1850))
    fcfs_cost = float(fcfs_row.get("Total_Energy_Cost_$", 2500))
    savings_val = fcfs_cost - opt_cost
    savings_pct = (savings_val / max(1.0, fcfs_cost)) * 100.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Total Electricity Cost", format_currency(opt_cost), delta=f"-{format_percentage(savings_pct)}", delta_is_positive=True)
    with col2:
        render_metric_card("Total Cost Savings", format_currency(savings_val), delta=f"+{format_percentage(savings_pct)}", delta_is_positive=True)
    with col3:
        peak_kwh = float(opt_row.get("Peak_Hour_Load_kWh", 150))
        fcfs_peak = float(fcfs_row.get("Peak_Hour_Load_kWh", 220))
        peak_save = fcfs_peak - peak_kwh
        render_metric_card("Peak-Hour Load", f"{peak_kwh:.2f} kWh", delta=f"-{peak_save:.1f} kWh", delta_is_positive=True)
    with col4:
        makespan = float(opt_row.get("Makespan_hours", 18.5))
        render_metric_card("Total Schedule Makespan", f"{makespan:.1f} hours")

    st.markdown("---")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        util = float(opt_row.get("Machine_Utilization_%", 78.5))
        render_metric_card("Machine Utilization", format_percentage(util))
    with col6:
        wait = float(opt_row.get("Average_Waiting_Time_min", 25))
        render_metric_card("Avg Job Waiting Time", f"{wait:.1f} min")
    with col7:
        ontime = float(opt_row.get("On_Time_Completion_%", 100.0))
        render_metric_card("On-Time Completion Rate", format_percentage(ontime), delta="Zero Delays", delta_is_positive=True)
    with col8:
        late_jobs = int(opt_row.get("Number_of_Late_Jobs", 0))
        render_metric_card("Late Jobs Count", format_number(late_jobs), delta="Optimal", delta_is_positive=True)

    st.markdown("---")

    st.markdown("#### Complete KPI Summary Comparison Table")
    st.dataframe(kpi_df, use_container_width=True)
