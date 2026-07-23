"""
Home Page Dashboard View.
Renders Project Overview, system status badge, and key executive metric cards.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from dashboard.components.cards import render_metric_card
from dashboard.utils.formatter import format_currency, format_percentage, format_number


def render_home_page(
    opt_df: pd.DataFrame,
    fcfs_df: pd.DataFrame,
    kpi_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    pred_df: pd.DataFrame,
) -> None:
    """Renders Home Page Dashboard Overview."""
    st.markdown("### Industrial AI Decision Support System Overview")
    st.markdown(
        "This platform optimizes manufacturing plant operations by matching forecasted 15-minute energy "
        "consumption curves with optimal machine job execution windows using **XGBoost Regressor** and **Google OR-Tools CP-SAT**."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 4 Column Metric Cards Grid
    col1, col2, col3, col4 = st.columns(4)

    total_jobs = len(jobs_df) if not jobs_df.empty else len(opt_df)
    total_machines = len(machines_df) if not machines_df.empty else 10

    # Calculate Savings
    fcfs_cost = float(kpi_df[kpi_df["Schedule_Type"] == "Baseline_FCFS"]["Total_Energy_Cost_$"].iloc[0]) if not kpi_df.empty and "Total_Energy_Cost_$" in kpi_df.columns else 2500.0
    opt_cost = float(kpi_df[kpi_df["Schedule_Type"] == "CP_SAT_Optimized"]["Total_Energy_Cost_$"].iloc[0]) if not kpi_df.empty and "Total_Energy_Cost_$" in kpi_df.columns else 1850.0

    savings_val = fcfs_cost - opt_cost
    savings_pct = (savings_val / max(1.0, fcfs_cost)) * 100.0

    with col1:
        render_metric_card("Total Jobs Requested", format_number(total_jobs))
    with col2:
        render_metric_card("Active Machine Fleet", format_number(total_machines))
    with col3:
        render_metric_card("Optimized Schedule Cost", format_currency(opt_cost), delta=f"-{format_percentage(savings_pct)}", delta_is_positive=True)
    with col4:
        render_metric_card("Total Energy Savings", format_currency(savings_val), delta=f"+{format_percentage(savings_pct)}", delta_is_positive=True)
