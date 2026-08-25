"""
Smart Machine Scheduling & Energy Optimization Dashboard.
Consolidated Single-Page Executive Dark UI.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.utils.loader import (
    load_all_schedules,
    load_predictions_data,
    load_job_and_machine_data,
    load_comprehensive_report
)

CUSTOM_CSS = """
<style>
/* ── Google Fonts ────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── App Background ──────────────────────────────────────────────────────── */
.stApp {
    background: #090d16 !important;
    color: #e2e8f0 !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}

/* ── Headings ────────────────────────────────────────────────────────────── */
h1, h2, h3, h4 {
    color: #f8fafc !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}
h2 { font-size: 1.6rem !important; margin-bottom: 0.8rem !important; }
h3 { font-size: 1.2rem !important; margin-top: 1rem !important; }

/* ── Dividers ────────────────────────────────────────────────────────────── */
hr {
    border-color: #1e293b !important;
    margin: 1.5rem 0 !important;
}

/* ── Metric Cards ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #131b2e 0%, #0d1323 100%) !important;
    border: 1px solid #1e293b !important;
    border-radius: 16px !important;
    padding: 20px 24px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.25s ease !important;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #6366f1, #a855f7);
    opacity: 0.8;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-4px) !important;
    border-color: #6366f1 !important;
    box-shadow: 0 16px 35px rgba(99, 102, 241, 0.15) !important;
}
[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

/* ── Custom HTML Tables ──────────────────────────────────────────────────── */
.benchmark-card {
    background: linear-gradient(135deg, #131b2e 0%, #0d1323 100%);
    border: 1px solid #1e293b;
    border-radius: 18px;
    padding: 24px;
    margin-top: 15px;
    margin-bottom: 25px;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5);
}
.benchmark-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 14px;
    border-bottom: 1px solid #1e293b;
}
.benchmark-title {
    font-size: 1.2rem;
    font-weight: 800;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 8px;
}
.benchmark-status-badge {
    background: rgba(99, 102, 241, 0.15);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
    font-size: 0.78rem;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.styled-benchmark-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.92rem;
}
.styled-benchmark-table th {
    background: #101626;
    color: #94a3b8;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    padding: 14px 20px;
    border-bottom: 2px solid #1e293b;
    text-align: left;
}
.styled-benchmark-table th:first-child { border-top-left-radius: 12px; }
.styled-benchmark-table th:last-child { border-top-right-radius: 12px; }
.styled-benchmark-table td {
    padding: 14px 20px;
    border-bottom: 1px solid #101626;
    color: #cbd5e1;
    vertical-align: middle;
}
.styled-benchmark-table tr:last-child td {
    border-bottom: none;
}
.styled-benchmark-table tr:hover td {
    background: rgba(99, 102, 241, 0.06);
}
.metric-name-col {
    font-weight: 700;
    color: #f1f5f9;
}
.val-fcfs {
    color: #f87171;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.val-selected {
    color: #818cf8;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.pill-improvement {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.pill-neutral {
    background: rgba(148, 163, 184, 0.1);
    color: #94a3b8;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    display: inline-flex;
}
.pill-worse {
    background: rgba(244, 63, 94, 0.1);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.25);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    display: inline-flex;
}

/* ── Page Header Banner ──────────────────────────────────────────────────── */
.page-header {
    background: linear-gradient(135deg, #131c31 0%, #080d1a 100%);
    border: 1px solid #1e293b;
    border-left: 5px solid #6366f1;
    border-radius: 18px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
}
.page-header h2 {
    margin: 0 !important;
    font-size: 1.7rem !important;
    background: linear-gradient(90deg, #ffffff, #a5b4fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.page-header p {
    color: #94a3b8;
    margin: 6px 0 0 0;
    font-size: 0.95rem;
    font-weight: 500;
}
.section-badge {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: #ffffff;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 8px;
}

/* ── Plotly Containers ────────────────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid #1e293b !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
    background: #131b2e !important;
}

/* ── Info Box ────────────────────────────────────────────────────────────── */
.stAlert {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 14px !important;
}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #090d16; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }
</style>
"""

DARK_LAYOUT = dict(
    paper_bgcolor="#131b2e",
    plot_bgcolor="#131b2e",
    font=dict(color="#cbd5e1", family="Plus Jakarta Sans, sans-serif"),
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b", linecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b", linecolor="#1e293b"),
)

PRIORITY_COLORS = {"High": "#fb7185", "Medium": "#fbbf24", "Low": "#34d399"}

MODEL_DISPLAY_NAMES = {
    "FCFS": "First Come First Served (FCFS)",
    "EDF": "Earliest Deadline First (EDF)",
    "Makespan_Greedy": "Makespan-Only Greedy",
    "Proposed_Robust_Greedy": "Robust Energy-Aware Greedy (Proposed)",
    "Deterministic_Greedy": "Deterministic Energy-Aware Greedy",
    "Hybrid_Solver": "Hybrid CP-SAT (Warm-start Optimized)"
}


def parse_val(v_str):
    if pd.isna(v_str):
        return 0.0
    v_str = str(v_str).replace("INR", "").replace("₹", "").replace("kW", "").replace("hrs", "").replace("%", "").replace("min", "").replace("t", "").replace("jobs", "").strip()
    try:
        return float(v_str)
    except ValueError:
        return 0.0


def _build_gantt_timeline(df: pd.DataFrame, title: str):
    if df.empty:
        return None
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
        **DARK_LAYOUT,
        title=dict(text=title, font=dict(color="#f8fafc", size=15, weight="bold")),
        height=400,
        legend=dict(title="Priority", font=dict(color="#cbd5e1"), bgcolor="#0f172a",
                    bordercolor="#1e293b", borderwidth=1),
        xaxis_title="", yaxis_title="Machine Fleet",
    )
    fig.update_yaxes(categoryorder="category ascending", tickfont=dict(color="#94a3b8"))
    fig.update_xaxes(tickfont=dict(color="#94a3b8"))
    return fig


def _build_demand_profile(fut_df: pd.DataFrame):
    if fut_df.empty or "predicted_kWh" not in fut_df.columns:
        return None

    ts_col = next((c for c in ["timestamp", "Datetime", "date"] if c in fut_df.columns), None)
    if not ts_col:
        return None

    fig = go.Figure()
    
    # Shade background regions according to Load_Type
    temp_df = fut_df.reset_index(drop=True)
    
    # Plot forecast lines
    # p10 (lower bound)
    if "predicted_kWh_p10" in temp_df.columns:
        fig.add_scatter(
            x=temp_df[ts_col], y=temp_df["predicted_kWh_p10"],
            name="Lower Bound Forecast (p10)",
            line=dict(color="#312e81", width=1, dash="dash"),
            mode="lines",
            showlegend=True
        )
    
    # p90 (upper bound / robust tariff planning boundary)
    if "predicted_kWh_p90" in temp_df.columns:
        fig.add_scatter(
            x=temp_df[ts_col], y=temp_df["predicted_kWh_p90"],
            name="Upper Bound Forecast (p90 - Robust)",
            line=dict(color="#818cf8", width=1, dash="dash"),
            mode="lines",
            fill="tonexty" if "predicted_kWh_p10" in temp_df.columns else None,
            fillcolor="rgba(99, 102, 241, 0.05)",
            showlegend=True
        )
        
    # Main p50 Forecasted Load
    fig.add_scatter(
        x=temp_df[ts_col], y=temp_df["predicted_kWh"],
        name="Median Forecast (p50 / Base)",
        line=dict(color="#6366f1", width=3),
        mode="lines",
    )

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text="24-Hour XGBoost Energy Demand Forecast (Multi-Quantile)", font=dict(color="#f8fafc", size=14, weight="bold")),
        height=320,
        yaxis_title="Energy Demand (kWh)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=9)),
    )
    return fig


def _build_machine_active_bar(df: pd.DataFrame, title_prefix: str):
    if df.empty:
        return None
    counts = df.groupby("Assigned_Machine").apply(
        lambda g: (g["End_Slot"] - g["Start_Slot"]).sum() * 15
    ).reset_index()
    counts.columns = ["Machine", "Active_min"]
    counts = counts.sort_values("Machine")

    fig = go.Figure(go.Bar(
        x=counts["Machine"], y=counts["Active_min"],
        marker=dict(
            color=counts["Active_min"],
            colorscale=[[0, "#4f46e5"], [0.5, "#6366f1"], [1, "#a855f7"]],
            showscale=False,
        ),
        text=counts["Active_min"].astype(int).astype(str) + " min",
        textposition="outside", textfont=dict(color="#cbd5e1", size=10),
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text=f"Active Operating Time per Machine ({title_prefix})", font=dict(color="#f8fafc", size=14, weight="bold")),
        height=320,
        xaxis_title="Machine ID", yaxis_title="Active Minutes",
    )
    return fig


def _build_overall_comparison_bar(comp_df: pd.DataFrame, metric_row: str, title: str, ylabel: str, is_currency: bool = False, format_str: str = "{:.1f}"):
    if comp_df.empty or metric_row not in comp_df.index:
        return None
    
    row = comp_df.loc[metric_row]
    x_keys = ["FCFS", "EDF", "Makespan_Greedy", "Deterministic_Greedy", "Proposed_Robust_Greedy", "Hybrid_Solver"]
    x_labels = ["FCFS (Baseline)", "EDF", "Makespan Greedy", "Det. Greedy", "Robust Greedy", "Hybrid CP-SAT"]
    y_vals = [parse_val(row[k]) for k in x_keys]
    
    colors = ["#f87171", "#fca5a5", "#fca5a5", "#818cf8", "#6366f1", "#4f46e5"]
    
    fig = go.Figure(go.Bar(
        x=x_labels, y=y_vals,
        marker_color=colors,
        text=[(f"₹{v:,.0f}" if is_currency else format_str.format(v)) for v in y_vals],
        textposition="outside", textfont=dict(color="#cbd5e1", size=10, weight="bold")
    ))
    
    # Merge DARK_LAYOUT to avoid duplicate xaxis keyword argument errors
    layout_args = DARK_LAYOUT.copy()
    layout_args["title"] = dict(text=title, font=dict(color="#f8fafc", size=14, weight="bold"))
    layout_args["height"] = 320
    layout_args["yaxis_title"] = ylabel
    layout_args["xaxis"] = {**DARK_LAYOUT.get("xaxis", {}), "tickangle": -15, "tickfont": dict(size=10)}
    
    fig.update_layout(**layout_args)
    return fig


def main():
    st.set_page_config(
        page_title="Smart Factory Scheduling AI",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── 1. DATA LOADING ──────────────────────────────────────────────────
    schedules = load_all_schedules()
    pred_df, fut_df = load_predictions_data()
    jobs_df, machines_df = load_job_and_machine_data()
    comp_raw = load_comprehensive_report()
    
    # Setup index for comprehensive report parsing
    comp_df = comp_raw.copy()
    if not comp_df.empty and "Metric" in comp_df.columns:
        comp_df.set_index("Metric", inplace=True)
    else:
        st.error("Comprehensive benchmark comparison report (comprehensive_report.csv) is missing or corrupted.")
        st.stop()

    # ── 2. HEADER BANNER ─────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div class="section-badge">Predict-then-Optimize Framework</div>
        <h2>Factory Operations &amp; Energy Optimization Dashboard</h2>
        <p>Interactive machine scheduling optimized for electricity cost, carbon emissions, and peak grid load.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. SIDEBAR CONTROLS ───────────────────────────────────────────────
    st.sidebar.markdown("### ⚙️ Scheduling Engine Options")
    selected_model_label = st.sidebar.selectbox(
        "Choose Scheduling Strategy",
        list(MODEL_DISPLAY_NAMES.values()),
        index=5 # Default: Hybrid CP-SAT
    )
    
    # Map back to model key
    selected_model_key = next(k for k, v in MODEL_DISPLAY_NAMES.items() if v == selected_model_label)
    
    st.sidebar.divider()
    
    st.sidebar.markdown("### 💡 Operations Trade-off Guide")
    st.sidebar.info(
        "**Energy Shifting vs. Timeline Punctuality**\n\n"
        "• **Baselines (FCFS/EDF/Makespan)** pack jobs as quickly as possible. This yields high machine utilization and short makespans, but runs massive peak grid loads at expensive times.\n\n"
        "• **Optimized Solvers (CP-SAT/Robust)** shift loads to off-peak slots. This reduces energy cost by up to **76%** and limits peak kW spikes, but increases waiting times and makespan."
    )
    
    # Selected schedule dataframe
    sel_sched_df = schedules.get(selected_model_key, pd.DataFrame())
    fcfs_sched_df = schedules.get("FCFS", pd.DataFrame())

    # ── 4. EXECUTIVE SCORECARD (SELECTED MODEL VS FCFS) ─────────────────
    st.markdown("### 📊 Executive KPI Comparison vs FCFS Baseline")
    
    # Parse core metrics for comparison
    cost_fcfs = parse_val(comp_df.loc["Total Energy Cost (INR)", "FCFS"])
    cost_sel  = parse_val(comp_df.loc["Total Energy Cost (INR)", selected_model_key])
    cost_diff = cost_fcfs - cost_sel
    cost_pct  = (cost_diff / max(1.0, cost_fcfs)) * 100.0
    
    peak_fcfs = parse_val(comp_df.loc["Peak Grid Load (kW)", "FCFS"])
    peak_sel  = parse_val(comp_df.loc["Peak Grid Load (kW)", selected_model_key])
    peak_diff = peak_fcfs - peak_sel
    
    util_fcfs = parse_val(comp_df.loc["Machine Utilization (%)", "FCFS"])
    util_sel  = parse_val(comp_df.loc["Machine Utilization (%)", selected_model_key])
    util_diff = util_sel - util_fcfs
    
    ontime_fcfs = parse_val(comp_df.loc["On-Time Completion (%)", "FCFS"])
    ontime_sel  = parse_val(comp_df.loc["On-Time Completion (%)", selected_model_key])
    ontime_diff = ontime_sel - ontime_fcfs
    
    carbon_fcfs = parse_val(comp_df.loc["Carbon Emissions (tCO2)", "FCFS"])
    carbon_sel  = parse_val(comp_df.loc["Carbon Emissions (tCO2)", selected_model_key])
    carbon_diff = carbon_fcfs - carbon_sel
    carbon_pct  = (carbon_diff / max(0.001, carbon_fcfs)) * 100.0

    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric(
            label="Total Electricity Cost",
            value=f"₹{cost_sel:,.2f}",
            delta=f"-₹{cost_diff:,.2f} ({cost_pct:.1f}% Saved)" if cost_diff >= 0 else f"+₹{abs(cost_diff):,.2f} (+{abs(cost_pct):.1f}%)",
            delta_color="normal" if cost_diff >= 0 else "inverse"
        )
        
    with c2:
        st.metric(
            label="Peak Grid Load",
            value=f"{peak_sel:.2f} kW",
            delta=f"-{peak_diff:.2f} kW (-{peak_diff/peak_fcfs*100:.1f}%)" if peak_diff >= 0 else f"+{abs(peak_diff):.2f} kW (+{abs(peak_diff)/peak_fcfs*100:.1f}%)",
            delta_color="normal" if peak_diff >= 0 else "inverse"
        )
        
    with c3:
        st.metric(
            label="Fleet Utilization",
            value=f"{util_sel:.2f}%",
            delta=f"{util_diff:+.2f} pp Change",
            delta_color="normal" if util_diff >= 0 else "off"
        )
        
    with c4:
        st.metric(
            label="On-Time Delivery Rate",
            value=f"{ontime_sel:.1f}%",
            delta=f"{ontime_diff:+.1f} pp Delivery Accuracy" if ontime_diff >= 0 else f"{ontime_diff:.1f} pp Delay Accrual",
            delta_color="normal" if ontime_diff >= 0 else "inverse"
        )
        
    st.divider()

    # ── 5. DETAILED ALGORITHMIC COMPARISON SECTION ─────────────────────
    st.markdown("### 🏆 Scheduling Benchmark Analytics")
    
    benchmark_tab1, benchmark_tab2, benchmark_tab3 = st.tabs([
        "  ⚖️ Target Model vs Baseline  ",
        "  📁 Full Comparative Matrix (All 6 Models)  ",
        "  📈 High-Level KPI Comparison Charts  "
    ])
    
    with benchmark_tab1:
        # Side-by-side HTML comparison table
        rows_html = ""
        for metric, row in comp_raw.iterrows():
            metric_name = row.get("Metric", "")
            fcfs_val = row.get("FCFS", "")
            sel_val = row.get(selected_model_key, "")
            
            f_num = parse_val(fcfs_val)
            s_num = parse_val(sel_val)
            
            is_lower_better = "cost" in metric_name.lower() or "load" in metric_name.lower() or "makespan" in metric_name.lower() or "wait" in metric_name.lower() or "idle" in metric_name.lower() or "delay" in metric_name.lower() or "late" in metric_name.lower() or "emission" in metric_name.lower()
            
            badge_class = "pill-neutral"
            icon = ""
            desc = ""
            
            if f_num == s_num:
                desc = "No Change"
            elif is_lower_better:
                if s_num < f_num:
                    badge_class = "pill-improvement"
                    icon = "✓ "
                    pct_val = ((f_num - s_num) / max(1.0, f_num)) * 100
                    desc = f"Saved {pct_val:.1f}%"
                else:
                    badge_class = "pill-worse"
                    pct_val = ((s_num - f_num) / max(1.0, f_num)) * 100
                    desc = f"Increased {pct_val:.1f}%"
            else:
                if s_num > f_num:
                    badge_class = "pill-improvement"
                    icon = "✓ "
                    pct_val = ((s_num - f_num) / max(1.0, f_num)) * 100
                    desc = f"Gained {pct_val:.1f}%"
                else:
                    badge_class = "pill-worse"
                    pct_val = ((f_num - s_num) / max(1.0, f_num)) * 100
                    desc = f"Reduced {pct_val:.1f}%"
                    
            if metric_name == "Power Factor Penalty (INR)" and f_num == 0 and s_num == 0:
                desc = "No Penalty Incurred"
                badge_class = "pill-neutral"
            
            rows_html += f"""
            <tr>
                <td class="metric-name-col">{metric_name}</td>
                <td class="val-fcfs">{fcfs_val}</td>
                <td class="val-selected">{sel_val}</td>
                <td><span class="{badge_class}">{icon}{desc}</span></td>
            </tr>
            """
            
        html_code = f"""
        <div class="benchmark-card">
            <div class="benchmark-card-header">
                <div class="benchmark-title">
                    ⚖️ {MODEL_DISPLAY_NAMES['FCFS']} vs. {selected_model_label}
                </div>
                <div class="benchmark-status-badge">
                    Carbon Reduction: {carbon_pct:.1f}%
                </div>
            </div>
            <table class="styled-benchmark-table">
                <thead>
                    <tr>
                        <th style="width: 35%;">Key Performance Indicator</th>
                        <th style="width: 20%;">FCFS Baseline</th>
                        <th style="width: 25%;">{selected_model_label}</th>
                        <th style="width: 20%;">Quantified Difference</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
        
    with benchmark_tab2:
        st.markdown("<p style='color:#94a3b8;font-size:0.85rem;margin-bottom:10px'>Full published benchmark report across all heuristics, greedy, and robust scheduling solvers.</p>", unsafe_allow_html=True)
        
        styled_comp_raw = comp_raw.copy()
        styled_comp_raw.columns = [
            "Metric", 
            "FCFS Baseline", 
            "Earliest Deadline First", 
            "Makespan Greedy", 
            "Robust Greedy (p90)", 
            "Deterministic Greedy (p50)", 
            "Hybrid CP-SAT (Warm-started)"
        ]
        st.dataframe(styled_comp_raw, use_container_width=True, hide_index=True)
        
    with benchmark_tab3:
        st.markdown("<p style='color:#94a3b8;font-size:0.85rem;margin-bottom:10px'>Visual comparison of performance metrics for all 6 models.</p>", unsafe_allow_html=True)
        row1, row2 = st.columns(2)
        
        with row1:
            fig_cost = _build_overall_comparison_bar(comp_df, "Total Energy Cost (INR)", "Total Electricity Cost Comparison (INR)", "INR (₹)", is_currency=True)
            if fig_cost:
                st.plotly_chart(fig_cost, use_container_width=True)
                
        with row2:
            fig_peak = _build_overall_comparison_bar(comp_df, "Peak Grid Load (kW)", "Peak Grid Load Comparison (kW)", "kW", format_str="{:.1f} kW")
            if fig_peak:
                st.plotly_chart(fig_peak, use_container_width=True)
                
        row3, row4 = st.columns(2)
        
        with row3:
            fig_ontime = _build_overall_comparison_bar(comp_df, "On-Time Completion (%)", "On-Time Delivery Rate (%)", "%", format_str="{:.1f}%")
            if fig_ontime:
                st.plotly_chart(fig_ontime, use_container_width=True)
                
        with row4:
            fig_emissions = _build_overall_comparison_bar(comp_df, "Carbon Emissions (tCO2)", "Total Greenhouse Gas Emissions (tCO2)", "tCO2", format_str="{:.2f} t")
            if fig_emissions:
                st.plotly_chart(fig_emissions, use_container_width=True)

    st.divider()

    # ── 6. TIMELINE & GANTT CHARTS ───────────────────────────────────────
    st.markdown("### 📅 Machine Scheduling Gantt Timeline")
    
    gantt_tab1, gantt_tab2 = st.tabs([
        f"  📋 {selected_model_label} Timeline  ",
        "  🔄 FCFS Baseline Schedule (Greedy Parallel)  "
    ])
    
    with gantt_tab1:
        if sel_sched_df.empty:
            st.warning(f"No schedule timeline data found for {selected_model_label}.")
        else:
            fig_gantt_sel = _build_gantt_timeline(sel_sched_df, f"Gantt Execution Plot ({selected_model_label})")
            if fig_gantt_sel:
                st.plotly_chart(fig_gantt_sel, use_container_width=True)
                
    with gantt_tab2:
        if fcfs_sched_df.empty:
            st.warning("No schedule timeline data found for FCFS baseline.")
        else:
            fig_gantt_fcfs = _build_gantt_timeline(fcfs_sched_df, "Gantt Execution Plot (FCFS Baseline)")
            if fig_gantt_fcfs:
                st.plotly_chart(fig_gantt_fcfs, use_container_width=True)
                
    st.divider()

    # ── 7. FORECASTING & FLEET OPERATIONAL METRICS ───────────────────────
    st.markdown("### 🔌 Forecasting Horizon & Machine Operating Fleet")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        fig_demand = _build_demand_profile(fut_df)
        if fig_demand:
            st.plotly_chart(fig_demand, use_container_width=True)
        else:
            st.info("No XGBoost forecasting data available.")
            
    with col_r:
        fig_mach = _build_machine_active_bar(sel_sched_df, selected_model_label)
        if fig_mach:
            st.plotly_chart(fig_mach, use_container_width=True)
        else:
            st.info("No active machine fleet statistics available for the selected model.")

    st.divider()

    # ── 8. DETAILED SCHEDULE LOGS ────────────────────────────────────────
    st.markdown("### 📋 Scheduled Operations Log")
    
    log_tabs = st.tabs(["Selected Schedule Table", "Machine Specification Reference"])
    
    with log_tabs[0]:
        if not sel_sched_df.empty:
            show_cols = ["Job_ID", "Assigned_Machine", "Machine_Type", "Start_Time", "End_Time", "Duration_min", "Priority", "Delay_min", "Energy_Cost_$"]
            existing_cols = [c for c in show_cols if c in sel_sched_df.columns]
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                priority_filter = st.multiselect("Filter by Job Priority", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
            with col_f2:
                machine_filter = st.multiselect("Filter by Machine", sorted(sel_sched_df["Assigned_Machine"].unique().tolist()), default=sorted(sel_sched_df["Assigned_Machine"].unique().tolist()))
                
            filtered_df = sel_sched_df[
                sel_sched_df["Priority"].isin(priority_filter) &
                sel_sched_df["Assigned_Machine"].isin(machine_filter)
            ]
            st.dataframe(filtered_df[existing_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.info("No scheduling logs available.")
            
    with log_tabs[1]:
        if not machines_df.empty:
            st.dataframe(machines_df, use_container_width=True, hide_index=True)
        else:
            st.info("No machine specification reference available.")


if __name__ == "__main__":
    main()
