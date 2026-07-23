"""
Settings & Export Dashboard View.
Renders UI configuration controls, Light/Dark theme selector, and dataset export options.
"""

import streamlit as st
import pandas as pd

from dashboard.utils.exporter import dataframe_to_csv_bytes, dataframe_to_excel_bytes


def render_settings_page(
    opt_df: pd.DataFrame,
    fcfs_df: pd.DataFrame,
    kpi_df: pd.DataFrame,
    pred_df: pd.DataFrame,
) -> None:
    """Renders Settings & Data Export Center Page."""
    st.markdown("### Settings & Dataset Export Center")
    st.caption("Configure display preferences, toggle UI themes, and export dataset artifacts")

    st.markdown("#### UI Theme & Visual Display Preferences")

    current_theme = st.session_state.get("theme_mode", "Light")
    new_theme = st.selectbox(
        label="Select UI Theme Mode",
        options=["Light", "Dark"],
        index=0 if current_theme == "Light" else 1,
    )

    if new_theme != current_theme:
        st.session_state["theme_mode"] = new_theme
        st.rerun()

    st.markdown("---")

    st.markdown("#### Download System Output Artifacts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 1. CP-SAT Optimized Schedule")
        if not opt_df.empty:
            csv_data = dataframe_to_csv_bytes(opt_df)
            excel_data = dataframe_to_excel_bytes(opt_df, sheet_name="OptimizedSchedule")

            st.download_button(
                label="Download Schedule (CSV)",
                data=csv_data,
                file_name="optimized_schedule.csv",
                mime="text/csv",
                key="dl_opt_csv",
            )
            st.download_button(
                label="Download Schedule (Excel XLSX)",
                data=excel_data,
                file_name="optimized_schedule.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_opt_xlsx",
            )
        else:
            st.info("No schedule data available.")

    with col2:
        st.markdown("##### 2. Energy Demand Forecasting Predictions")
        if not pred_df.empty:
            pred_csv = dataframe_to_csv_bytes(pred_df)
            pred_excel = dataframe_to_excel_bytes(pred_df, sheet_name="Predictions")

            st.download_button(
                label="Download Predictions (CSV)",
                data=pred_csv,
                file_name="predictions.csv",
                mime="text/csv",
                key="dl_pred_csv",
            )
            st.download_button(
                label="Download Predictions (Excel XLSX)",
                data=pred_excel,
                file_name="predictions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_pred_xlsx",
            )
        else:
            st.info("No prediction data available.")

    st.markdown("---")

    st.markdown("#### System Configuration Parameters")

    st.slider("Peak Tariff Threshold Rate ($/kWh)", min_value=0.10, max_value=0.50, value=0.25, step=0.01)
    st.slider("Target Machine Utilization (%)", min_value=50, max_value=95, value=75, step=5)
