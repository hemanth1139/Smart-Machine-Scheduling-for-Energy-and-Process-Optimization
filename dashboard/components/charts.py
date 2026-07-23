"""
Enterprise Plotly Charts Component Module.
Constructs corporate, publication-quality Plotly visualizers for energy demand forecasting and machine scheduling.
"""

from typing import Optional, List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# Corporate Color Palette
COLOR_PRIMARY = "#2563EB"
COLOR_SUCCESS = "#22C55E"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_NEUTRAL = "#64748B"


def apply_corporate_layout(fig: go.Figure, title: str, x_title: str, y_title: str, height: int = 400) -> go.Figure:
    """Applies corporate Plotly design template."""
    fig.update_layout(
        title=dict(text=title, font=dict(family="Inter, sans-serif", size=15, color="#0F172A")),
        xaxis=dict(
            title=dict(text=x_title, font=dict(size=12, color="#64748B")),
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=12, color="#64748B")),
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=False,
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter, sans-serif", color="#0F172A"),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Inter, sans-serif"),
        margin=dict(l=40, r=20, t=50, b=40),
        height=height,
    )
    return fig


def build_gantt_chart(df: pd.DataFrame) -> go.Figure:
    """Constructs corporate Plotly Gantt chart for machine job schedules."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No schedule data available", showarrow=False, font=dict(size=14))
        return fig

    df_plot = df.copy()

    # Enterprise Machine Color Mapping
    machine_colors = {
        "M1": "#2563EB", "M2": "#3B82F6", "M3": "#60A5FA",
        "M4": "#22C55E", "M5": "#10B981", "M6": "#059669",
        "M7": "#F59E0B", "M8": "#D97706", "M9": "#8B5CF6", "M10": "#EC4899"
    }

    fig = px.timeline(
        df_plot,
        x_start=pd.to_datetime("2026-01-01") + pd.to_timedelta(df_plot["Start_Slot"] * 15, unit="m"),
        x_end=pd.to_datetime("2026-01-01") + pd.to_timedelta(df_plot["End_Slot"] * 15, unit="m"),
        y="Assigned_Machine",
        color="Assigned_Machine",
        hover_name="Job_ID",
        hover_data=["Start_Time", "End_Time", "Duration_min", "Priority", "Delay_min", "Energy_Cost_$"],
        title="Production Job Execution Timeline (Gantt Chart)",
        color_discrete_map=machine_colors,
    )

    fig.update_yaxes(autorange="reversed")
    fig = apply_corporate_layout(fig, "Production Job Execution Timeline (Gantt Chart)", "Schedule Time Slot (15-min Intervals)", "Machine Resource", height=450)
    return fig


def build_machine_timeline(df: pd.DataFrame) -> go.Figure:
    """Constructs Machine Operating Minutes bar chart."""
    if df.empty:
        return go.Figure()

    machine_counts = df.groupby(["Assigned_Machine", "Machine_Type"])["Duration_min"].sum().reset_index()

    fig = px.bar(
        machine_counts,
        x="Assigned_Machine",
        y="Duration_min",
        color="Machine_Type",
        title="Total Active Operating Minutes per Machine",
        color_discrete_sequence=px.colors.sequential.Blues[2:],
    )
    fig = apply_corporate_layout(fig, "Total Active Operating Minutes per Machine", "Machine ID", "Active Minutes", height=380)
    return fig


def build_job_allocation(df: pd.DataFrame) -> go.Figure:
    """Constructs Job Workload Allocation bar chart."""
    if df.empty:
        return go.Figure()

    counts = df["Assigned_Machine"].value_counts().sort_index().reset_index()
    counts.columns = ["Machine", "Job_Count"]

    fig = px.bar(
        counts,
        x="Machine",
        y="Job_Count",
        text="Job_Count",
        title="Job Workload Allocation per Machine Resource",
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig.update_traces(textposition="outside")
    fig = apply_corporate_layout(fig, "Job Workload Allocation per Machine Resource", "Assigned Machine", "Job Count", height=380)
    return fig


def build_actual_vs_predicted_chart(df: pd.DataFrame, sample_size: int = 300) -> go.Figure:
    """Constructs line plot comparing Actual vs Predicted energy usage."""
    if df.empty:
        return go.Figure()

    df_sub = df.iloc[:sample_size] if len(df) > sample_size else df

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sub["timestamp"],
            y=df_sub["actual_kWh"],
            mode="lines",
            name="Actual Usage (kWh)",
            line=dict(color=COLOR_PRIMARY, width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_sub["timestamp"],
            y=df_sub["predicted_kWh"],
            mode="lines",
            name="XGBoost Forecast (kWh)",
            line=dict(color=COLOR_DANGER, width=1.8, dash="dash"),
        )
    )

    fig = apply_corporate_layout(fig, "Actual vs Predicted Energy Consumption Profile", "Timestamp", "Usage (kWh)", height=400)
    fig.update_layout(hovermode="x unified", legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"))
    return fig


def build_future_forecast_chart(df_future: pd.DataFrame) -> go.Figure:
    """Constructs 24h future forecast line plot."""
    if df_future.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_future["timestamp"],
            y=df_future["predicted_kWh"],
            mode="lines+markers",
            name="Predicted Demand",
            line=dict(color=COLOR_SUCCESS, width=2.5),
            marker=dict(size=4),
        )
    )

    fig = apply_corporate_layout(fig, "24-Hour Ahead Forecasted Energy Profile (Phase 3 Optimizer Input)", "Time Slot", "Predicted kWh", height=380)
    fig.update_layout(hovermode="x unified")
    return fig


def build_error_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Constructs histogram of prediction residual errors."""
    if df.empty:
        return go.Figure()

    fig = px.histogram(
        df,
        x="residual_error",
        nbins=40,
        title="Prediction Residual Error Distribution (kWh)",
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig = apply_corporate_layout(fig, "Prediction Residual Error Distribution (kWh)", "Residual Error (kWh)", "Frequency", height=380)
    return fig


def build_residual_chart(df: pd.DataFrame) -> go.Figure:
    """Constructs scatter plot of Residuals vs Predicted values."""
    if df.empty:
        return go.Figure()

    fig = px.scatter(
        df,
        x="predicted_kWh",
        y="residual_error",
        opacity=0.5,
        title="Residual Error vs Predicted Values",
        color_discrete_sequence=[COLOR_NEUTRAL],
    )
    fig.add_hline(y=0, line_dash="dash", line_color=COLOR_DANGER)
    fig = apply_corporate_layout(fig, "Residual Error vs Predicted Values", "Predicted kWh", "Residual Error", height=380)
    return fig


def build_feature_importance_chart(fi_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Constructs horizontal bar chart of feature importances."""
    if fi_df.empty:
        return go.Figure()

    top_fi = fi_df.head(top_n).sort_values(by="Importance", ascending=True)

    fig = px.bar(
        top_fi,
        x="Importance",
        y="Feature",
        orientation="h",
        title=f"XGBoost Feature Importance Ranking (Top {top_n})",
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig = apply_corporate_layout(fig, f"XGBoost Feature Importance Ranking (Top {top_n})", "Gain Score", "Feature Column", height=400)
    return fig


def build_cost_comparison_chart(opt_cost: float, fcfs_cost: float) -> go.Figure:
    """Constructs bar chart comparing FCFS vs CP-SAT electricity cost."""
    diff = fcfs_cost - opt_cost
    pct = (diff / max(1.0, fcfs_cost)) * 100.0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["Baseline (FCFS)", "CP-SAT Optimized"],
            y=[fcfs_cost, opt_cost],
            marker_color=[COLOR_DANGER, COLOR_SUCCESS],
            text=[f"₹{fcfs_cost:,.2f}", f"₹{opt_cost:,.2f}"],
            textposition="auto",
        )
    )

    fig = apply_corporate_layout(fig, f"Total Electricity Cost (₹{diff:.2f} | {pct:.1f}% Savings)", "Scheduling Method", "Cost (₹)", height=380)
    return fig


def build_machine_utilization_chart(opt_df: pd.DataFrame, horizon_slots: int = 96) -> go.Figure:
    """Constructs bar chart for machine utilization percentage."""
    if opt_df.empty:
        return go.Figure()

    m_active = opt_df.groupby("Assigned_Machine").apply(lambda g: (g["End_Slot"] - g["Start_Slot"]).sum())
    m_util = (m_active / horizon_slots) * 100.0

    util_df = pd.DataFrame({"Machine": m_util.index, "Utilization_%": m_util.values})

    fig = px.bar(
        util_df,
        x="Machine",
        y="Utilization_%",
        text="Utilization_%",
        title="Machine Resource Utilization Percentage (%)",
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig = apply_corporate_layout(fig, "Machine Resource Utilization Percentage (%)", "Machine ID", "Utilization (%)", height=380)
    fig.update_layout(yaxis_range=[0, 115])
    return fig


def build_peak_load_comparison_chart(opt_df: pd.DataFrame, fcfs_df: pd.DataFrame, horizon: int = 96) -> go.Figure:
    """Constructs line chart comparing hourly active load profile."""
    opt_load = np.zeros(horizon)
    fcfs_load = np.zeros(horizon)

    if not opt_df.empty:
        for _, row in opt_df.iterrows():
            for t in range(int(row["Start_Slot"]), min(horizon, int(row["End_Slot"]))):
                opt_load[t] += 15.0

    if not fcfs_df.empty:
        for _, row in fcfs_df.iterrows():
            for t in range(int(row["Start_Slot"]), min(horizon, int(row["End_Slot"]))):
                fcfs_load[t] += 15.0

    slots = np.arange(horizon)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=slots, y=fcfs_load, mode="lines", name="Baseline FCFS (kW)", line=dict(color=COLOR_DANGER, dash="dash", width=2)))
    fig.add_trace(go.Scatter(x=slots, y=opt_load, mode="lines", name="CP-SAT Optimized (kW)", line=dict(color=COLOR_SUCCESS, width=2.5)))

    fig = apply_corporate_layout(fig, "Hourly Active Power Demand Profile & Peak Load Shift", "Time Slot (15-min)", "Power Load (kW)", height=380)
    fig.update_layout(hovermode="x unified", legend=dict(x=0.01, y=0.99))
    return fig
