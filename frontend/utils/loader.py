"""
Data Loader for Streamlit frontend.
Loads scheduling, forecasting, and job/machine CSVs from config locations.
"""

from pathlib import Path
from typing import Tuple
import streamlit as st
import pandas as pd

from backend.config import config


@st.cache_data(ttl=30)
def load_scheduling_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load optimized schedule, EDF/FCFS schedule, KPI summary, and comparison CSV."""
    out = config.OUTPUT_DIR
    opt_df   = pd.read_csv(out / "optimized_schedule.csv")   if (out / "optimized_schedule.csv").exists()   else pd.DataFrame()
    fcfs_df  = pd.read_csv(out / "fcfs_schedule.csv")        if (out / "fcfs_schedule.csv").exists()        else pd.DataFrame()
    kpi_df   = pd.read_csv(out / "kpi_summary.csv")          if (out / "kpi_summary.csv").exists()          else pd.DataFrame()
    comp_df  = pd.read_csv(out / "comparison_report.csv")    if (out / "comparison_report.csv").exists()    else pd.DataFrame()
    return opt_df, fcfs_df, kpi_df, comp_df


@st.cache_data(ttl=30)
def load_all_schedules() -> dict:
    """Load all 6 scheduling dataframes into a dictionary."""
    out = config.OUTPUT_DIR
    schedules = {
        "FCFS": pd.read_csv(out / "fcfs_schedule.csv") if (out / "fcfs_schedule.csv").exists() else pd.DataFrame(),
        "EDF": pd.read_csv(out / "edf_schedule.csv") if (out / "edf_schedule.csv").exists() else pd.DataFrame(),
        "Makespan_Greedy": pd.read_csv(out / "makespan_schedule.csv") if (out / "makespan_schedule.csv").exists() else pd.DataFrame(),
        "Proposed_Robust_Greedy": pd.read_csv(out / "robust_schedule.csv") if (out / "robust_schedule.csv").exists() else pd.DataFrame(),
        "Deterministic_Greedy": pd.read_csv(out / "deterministic_schedule.csv") if (out / "deterministic_schedule.csv").exists() else pd.DataFrame(),
        "Hybrid_Solver": pd.read_csv(out / "hybrid_schedule.csv") if (out / "hybrid_schedule.csv").exists() else pd.DataFrame()
    }
    return schedules


@st.cache_data(ttl=30)
def load_comprehensive_report() -> pd.DataFrame:
    """Load the comprehensive benchmark comparison report."""
    path = config.OUTPUT_DIR / "comprehensive_report.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data(ttl=30)
def load_predictions_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load predictions and future forecast."""
    pred_path = config.OUTPUT_DIR / "predictions.csv"
    fut_path  = config.OUTPUT_DIR / "future_forecast.csv"
    pred_df = pd.read_csv(pred_path) if pred_path.exists() else pd.DataFrame()
    fut_df  = pd.read_csv(fut_path)  if fut_path.exists()  else pd.DataFrame()
    return pred_df, fut_df


@st.cache_data(ttl=30)
def load_job_and_machine_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load processed job and machine datasets."""
    job_path  = config.PROCESSED_DATA_DIR / "jobs_cleaned.csv"
    mach_path = config.PROCESSED_DATA_DIR / "machines_cleaned.csv"
    jobs_df     = pd.read_csv(job_path)  if job_path.exists()  else pd.DataFrame()
    machines_df = pd.read_csv(mach_path) if mach_path.exists() else pd.DataFrame()
    return jobs_df, machines_df

