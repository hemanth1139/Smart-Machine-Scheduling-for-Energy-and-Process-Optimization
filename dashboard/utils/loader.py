"""
Dashboard Data Loader Module.
Loads existing CSV dataset outputs and markdown reports with Streamlit caching and path safety.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import streamlit as st
import pandas as pd

from config.config import Config, config
from dashboard.utils.logger import dash_logger


@st.cache_data(ttl=5)
def load_predictions_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads test set predictions and 24h future forecast CSVs generated in Phase 2.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (predictions_df, future_forecast_df)
    """
    pred_path = Config.PREDICTIONS_CSV_PATH
    fut_path = Config.FUTURE_FORECAST_CSV_PATH

    if pred_path.exists():
        dash_logger.info(f"Dashboard loading predictions from: {pred_path}")
        pred_df = pd.read_csv(pred_path)
    else:
        dash_logger.warning(f"Predictions file not found at {pred_path}. Creating fallback frame.")
        pred_df = pd.DataFrame(columns=["timestamp", "actual_kWh", "predicted_kWh", "residual_error", "abs_error", "pct_error"])

    if fut_path.exists():
        dash_logger.info(f"Dashboard loading future forecast from: {fut_path}")
        fut_df = pd.read_csv(fut_path)
    else:
        dash_logger.warning(f"Future forecast file not found at {fut_path}. Creating fallback frame.")
        fut_df = pd.DataFrame(columns=["timestamp", "predicted_kWh", "hour", "day_of_week", "is_weekend"])

    return pred_df, fut_df


@st.cache_data(ttl=5)
def load_scheduling_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads optimized schedule, FCFS schedule, KPI summary, and comparison CSVs generated in Phase 3.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        (optimized_df, fcfs_df, kpi_summary_df, comparison_df)
    """
    out_dir = Config.SCHEDULING_OUTPUT_DIR

    opt_path = out_dir / Config.OPTIMIZED_SCHEDULE_FILENAME
    fcfs_path = out_dir / Config.FCFS_SCHEDULE_FILENAME
    kpi_path = out_dir / Config.KPI_SUMMARY_FILENAME
    comp_path = out_dir / Config.COMPARISON_REPORT_FILENAME

    opt_df = pd.read_csv(opt_path) if opt_path.exists() else pd.DataFrame()
    fcfs_df = pd.read_csv(fcfs_path) if fcfs_path.exists() else pd.DataFrame()
    kpi_df = pd.read_csv(kpi_path) if kpi_path.exists() else pd.DataFrame()
    comp_df = pd.read_csv(comp_path) if comp_path.exists() else pd.DataFrame()

    return opt_df, fcfs_df, kpi_df, comp_df


@st.cache_data(ttl=5)
def load_job_and_machine_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads processed Job and Machine datasets safely.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (jobs_df, machines_df)
    """
    job_path = Config.PROCESSED_DATA_DIR / Config.JOB_CLEANED_FILENAME
    if not job_path.exists():
        job_path = Config.get_raw_path(Config.JOB_DATA_FILENAME)

    mach_path = Config.PROCESSED_DATA_DIR / Config.MACHINE_CLEANED_FILENAME
    if not mach_path.exists():
        mach_path = Config.get_raw_path(Config.MACHINE_DATA_FILENAME)

    jobs_df = pd.read_csv(job_path) if job_path.exists() else pd.DataFrame()
    machines_df = pd.read_csv(mach_path) if mach_path.exists() else pd.DataFrame()

    return jobs_df, machines_df


@st.cache_data(ttl=5)
def load_markdown_report(report_filename: str) -> str:
    """
    Reads markdown report file content securely.

    Args:
        report_filename: Name of the report markdown file (e.g. 'scheduling_report.md').

    Returns:
        str: Markdown string content.
    """
    safe_filename = Path(report_filename).name
    report_path = (Config.REPORTS_OUTPUT_DIR / safe_filename).resolve()

    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()

    return f"**Report file `{safe_filename}` not found in outputs/reports.**"
