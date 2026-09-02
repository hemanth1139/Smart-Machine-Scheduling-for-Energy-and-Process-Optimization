"""
Machine Scheduling Page — premium dark-themed Gantt + tables.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

MINIMAL_LIGHT_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(color="#334155", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=44, b=16),
    xaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#e2e8f0", linecolor="#e2e8f0"),
    yaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#e2e8f0", linecolor="#e2e8f0"),
)

PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}


def _gantt(df: pd.DataFrame):
    plot = df.copy()
    base = pd.Timestamp("2024-01-01")
    plot["Start"] = base + pd.to_timedelta(plot["Start_Slot"] * 15, unit="min")
    plot["Finish"] = base + pd.to_timedelta(plot["End_Slot"] * 15, unit="min")

    fig = px.timeline(
        plot,
        x_start="Start", x_end="Finish",
        y="Assigned_Machine",
        color="Priority",
        hover_data=["Job_ID", "Machine_Type", "Duration_min", "Energy_Cost_$"],
        color_discrete_map=PRIORITY_COLORS,
    )
    fig.update_layout(
        **MINIMAL_LIGHT_LAYOUT,
        title=dict(text="CP-SAT Optimized Job Execution Timeline", font=dict(color="#0f172a", size=14)),
        height=420,
        legend=dict(title="Priority", font=dict(color="#334155"), bgcolor="#ffffff",
                    bordercolor="#e2e8f0", borderwidth=1),
        xaxis_title="", yaxis_title="Machine",
    )
    fig.update_yaxes(categoryorder="category ascending", tickfont=dict(color="#64748b"))
    fig.update_xaxes(tickfont=dict(color="#64748b"))
    return fig


def _machine_bar(df: pd.DataFrame):
    """Active minutes per machine bar chart."""
    counts = df.groupby("Assigned_Machine").apply(
        lambda g: (g["End_Slot"] - g["Start_Slot"]).sum() * 15
    ).reset_index()
    counts.columns = ["Machine", "Active_min"]
    counts = counts.sort_values("Machine")

    fig = go.Figure(go.Bar(
        x=counts["Machine"], y=counts["Active_min"],
        marker=dict(
            color=counts["Active_min"],
            colorscale=[[0, "#818cf8"], [0.5, "#4f46e5"], [1, "#3730a3"]],
            showscale=False,
        ),
        text=counts["Active_min"].astype(int).astype(str) + " min",
        textposition="outside", textfont=dict(color="#475569", size=10),
    ))
    fig.update_layout(
        **MINIMAL_LIGHT_LAYOUT,
        title=dict(text="Active Operating Time per Machine", font=dict(color="#0f172a", size=13)),
        height=300,
        xaxis_title="Machine", yaxis_title="Minutes",
    )
    return fig



def render_scheduling_page(opt_df: pd.DataFrame, fcfs_df: pd.DataFrame) -> None:
    st.markdown("""
    <div class="page-header">
        <div class="section-badge">Phase 3 · OR-Tools CP-SAT</div>
        <h2>Machine Scheduling Engine</h2>
        <p>Intelligent job scheduling optimized for energy cost, peak load, and on-time delivery</p>
    </div>
    """, unsafe_allow_html=True)

    if opt_df.empty:
        st.warning("No schedule data found. Run `python main_phase3.py` first.")
        return

    # ── Headline metrics ─────────────────────────────────────────────────
    total_jobs = len(opt_df)
    active_m   = opt_df["Assigned_Machine"].nunique()
    total_cost = float(opt_df["Energy_Cost_$"].sum()) if "Energy_Cost_$" in opt_df.columns else 0.0
    late_count = int(opt_df["Is_Late"].sum())         if "Is_Late"       in opt_df.columns else 0
    on_time_pct = (1 - late_count / max(1, total_jobs)) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scheduled Jobs",        f"{total_jobs}")
    c2.metric("Active Machines",       f"{active_m}")
    c3.metric("Total Energy Cost",     f"₹{total_cost:,.2f}")
    c4.metric("On-Time Completion",    f"{on_time_pct:.0f}%",
              delta="All On-Time ✓" if late_count == 0 else f"{late_count} late")

    st.divider()

    # ── Gantt Chart ──────────────────────────────────────────────────────
    st.plotly_chart(_gantt(opt_df), use_container_width=True)

    st.divider()

    # ── Machine activity bar ─────────────────────────────────────────────
    st.plotly_chart(_machine_bar(opt_df), use_container_width=True)

    st.divider()

    # ── Schedule tables in tabs ──────────────────────────────────────────
    st.markdown('<p style="color:#64748b;font-size:.75rem;font-weight:600;letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px">Schedule Data</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["  CP-SAT Optimized  ", "  FCFS Baseline  "])
    cols = ["Job_ID", "Assigned_Machine", "Machine_Type",
            "Start_Time", "End_Time", "Duration_min",
            "Priority", "Delay_min", "Energy_Cost_$"]

    with tab1:
        show = [c for c in cols if c in opt_df.columns]
        st.dataframe(opt_df[show].reset_index(drop=True),
                     use_container_width=True, hide_index=True)

    with tab2:
        if not fcfs_df.empty:
            show_f = [c for c in cols if c in fcfs_df.columns]
            st.dataframe(fcfs_df[show_f].reset_index(drop=True),
                         use_container_width=True, hide_index=True)
        else:
            st.info("FCFS baseline data not available.")
