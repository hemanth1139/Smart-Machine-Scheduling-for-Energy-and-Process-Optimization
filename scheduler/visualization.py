"""
Scheduling Visualizer Module.
Generates 7 publication-quality visualization figures for schedule inspection and KPI comparisons saved to outputs/scheduling.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class SchedulingVisualizer:
    """Generates visual analytics suite for machine schedules and baseline comparisons."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Config.SCHEDULING_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="colorblind")
        plt.rcParams.update({"font.sans-serif": "DejaVu Sans", "font.family": "sans-serif"})

    def generate_all_plots(
        self,
        opt_df: pd.DataFrame,
        fcfs_df: pd.DataFrame,
        opt_kpis: Dict[str, Any],
        fcfs_kpis: Dict[str, Any],
    ) -> None:
        """
        Executes complete visualization suite generating all 7 required figures.

        Args:
            opt_df: CP-SAT Optimized Schedule DataFrame.
            fcfs_df: FCFS Baseline Schedule DataFrame.
            opt_kpis: CP-SAT KPI dictionary.
            fcfs_kpis: FCFS KPI dictionary.
        """
        logger.info("Starting automated scheduling visualization plot generation...")

        self.plot_gantt_chart(opt_df)
        self.plot_machine_timeline(opt_df)
        self.plot_job_allocation(opt_df)
        self.plot_machine_utilization(opt_df)
        self.plot_cost_comparison(opt_kpis, fcfs_kpis)
        self.plot_kpi_dashboard(opt_kpis, fcfs_kpis)
        self.plot_peak_load_comparison(opt_df, fcfs_df)

        logger.info(f"All 7 scheduling figures successfully saved to {self.output_dir}")

    def plot_gantt_chart(self, df: pd.DataFrame) -> None:
        """Generates Gantt Chart visualizing job execution blocks across machines over time slots."""
        save_path = self.output_dir / "gantt_chart.png"
        fig, ax = plt.subplots(figsize=(14, 8), dpi=300)

        machines = sorted(df["Assigned_Machine"].unique())
        colors = plt.cm.tab20(np.linspace(0, 1, len(df)))

        for i, (_, row) in enumerate(df.iterrows()):
            m_idx = machines.index(row["Assigned_Machine"])
            start = row["Start_Slot"]
            duration = row["End_Slot"] - start
            job_id = row["Job_ID"]

            ax.barh(
                y=m_idx,
                width=duration,
                left=start,
                color=colors[i % len(colors)],
                edgecolor="black",
                alpha=0.85,
                height=0.6,
            )
            
            # Label job ID inside bar if duration is sufficiently wide
            if duration >= 2:
                ax.text(
                    start + duration / 2.0,
                    m_idx,
                    job_id,
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=8,
                    fontweight="bold",
                )

        ax.set_yticks(range(len(machines)))
        ax.set_yticklabels(machines, fontsize=11, fontweight="bold")
        ax.set_xlabel("Time Slot Index (15-min resolution)", fontsize=12)
        ax.set_ylabel("Machine Resource", fontsize=12)
        ax.set_title("CP-SAT Optimized Job Schedule Gantt Chart", fontsize=14, fontweight="bold", pad=15)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_machine_timeline(self, df: pd.DataFrame) -> None:
        """Generates Machine Activity Status Timeline (Active vs Idle status)."""
        save_path = self.output_dir / "machine_timeline.png"
        fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

        machine_counts = df.groupby(["Assigned_Machine", "Machine_Type"])["Duration_min"].sum().reset_index()

        sns.barplot(x="Assigned_Machine", y="Duration_min", hue="Machine_Type", data=machine_counts, palette="magma", ax=ax)

        ax.set_title("Total Active Operating Minutes per Machine", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Machine ID", fontsize=12)
        ax.set_ylabel("Total Active Execution (Minutes)", fontsize=12)
        ax.legend(title="Machine Type", fontsize=10)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_job_allocation(self, df: pd.DataFrame) -> None:
        """Generates Job Count Allocation breakdown across machines."""
        save_path = self.output_dir / "job_allocation.png"
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        counts = df["Assigned_Machine"].value_counts().sort_index()

        sns.barplot(x=counts.index, y=counts.values, palette="viridis", ax=ax)
        
        for p in ax.patches:
            ax.annotate(
                f"{int(p.get_height())}",
                (p.get_x() + p.get_width() / 2.0, p.get_height()),
                ha="center",
                va="center",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
            )

        ax.set_title("Job Workload Allocation per Machine Resource", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Assigned Machine", fontsize=12)
        ax.set_ylabel("Number of Assigned Jobs", fontsize=12)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_machine_utilization(self, df: pd.DataFrame) -> None:
        """Generates Machine Utilization Percentage Bar Chart."""
        save_path = self.output_dir / "machine_utilization.png"
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        horizon = Config.SCHEDULING_HORIZON_SLOTS
        m_active_slots = df.groupby("Assigned_Machine").apply(lambda g: (g["End_Slot"] - g["Start_Slot"]).sum())
        m_util_pct = (m_active_slots / horizon) * 100.0

        sns.barplot(x=m_util_pct.index, y=m_util_pct.values, palette="crest", ax=ax)
        
        for p in ax.patches:
            ax.annotate(
                f"{p.get_height():.1f}%",
                (p.get_x() + p.get_width() / 2.0, p.get_height()),
                ha="center",
                va="center",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=9,
            )

        ax.set_title("Machine Utilization Percentage (%)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Machine ID", fontsize=12)
        ax.set_ylabel("Utilization (%)", fontsize=12)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_cost_comparison(self, opt_kpis: Dict[str, Any], fcfs_kpis: Dict[str, Any]) -> None:
        """Generates Total Energy Cost comparison bar chart (FCFS vs CP-SAT)."""
        save_path = self.output_dir / "cost_comparison.png"
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

        methods = ["Baseline (FCFS)", "CP-SAT Optimized"]
        costs = [fcfs_kpis.get("Total_Energy_Cost_$", 0), opt_kpis.get("Total_Energy_Cost_$", 0)]

        colors = ["#d62728", "#2ca02c"]
        bars = ax.bar(methods, costs, color=colors, width=0.5, edgecolor="black")

        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"₹{height:,.2f}",
                (bar.get_x() + bar.get_width() / 2.0, height),
                ha="center",
                va="bottom",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=11,
                fontweight="bold",
            )

        savings = fcfs_kpis.get("Total_Energy_Cost_$", 0) - opt_kpis.get("Total_Energy_Cost_$", 0)
        pct_savings = (savings / max(1, fcfs_kpis.get("Total_Energy_Cost_$", 1))) * 100.0
        
        ax.set_title(f"Total Electricity Cost Comparison\n(Cost Reduction: ₹{savings:.2f} | {pct_savings:.1f}% Savings)", fontsize=13, fontweight="bold", pad=15)
        ax.set_ylabel("Total Electricity Cost (₹)", fontsize=12)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_kpi_dashboard(self, opt_kpis: Dict[str, Any], fcfs_kpis: Dict[str, Any]) -> None:
        """Generates Multi-panel KPI summary card dashboard figure."""
        save_path = self.output_dir / "kpi_dashboard.png"
        fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=300)

        # 1. Total Energy Cost ($)
        ax1 = axes[0, 0]
        ax1.bar(["FCFS", "CP-SAT"], [fcfs_kpis.get("Total_Energy_Cost_$", 0), opt_kpis.get("Total_Energy_Cost_$", 0)], color=["#ff7f0e", "#1f77b4"])
        ax1.set_title("Total Energy Cost (₹)", fontsize=11, fontweight="bold")

        # 2. Peak Hour Load (kWh)
        ax2 = axes[0, 1]
        ax2.bar(["FCFS", "CP-SAT"], [fcfs_kpis.get("Peak_Hour_Load_kWh", 0), opt_kpis.get("Peak_Hour_Load_kWh", 0)], color=["#d62728", "#2ca02c"])
        ax2.set_title("Peak-Hour Load (kWh)", fontsize=11, fontweight="bold")

        # 3. Makespan (Hours)
        ax3 = axes[1, 0]
        ax3.bar(["FCFS", "CP-SAT"], [fcfs_kpis.get("Makespan_hours", 0), opt_kpis.get("Makespan_hours", 0)], color=["#9467bd", "#8c564b"])
        ax3.set_title("Makespan (Hours)", fontsize=11, fontweight="bold")

        # 4. On-Time Completion (%)
        ax4 = axes[1, 1]
        ax4.bar(["FCFS", "CP-SAT"], [fcfs_kpis.get("On_Time_Completion_%", 0), opt_kpis.get("On_Time_Completion_%", 0)], color=["#e377c2", "#17becf"])
        ax4.set_title("On-Time Completion Rate (%)", fontsize=11, fontweight="bold")
        ax4.set_ylim(0, 100)

        plt.suptitle("Scheduling KPI Benchmark Dashboard: Baseline vs CP-SAT", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_peak_load_comparison(self, opt_df: pd.DataFrame, fcfs_df: pd.DataFrame) -> None:
        """Generates Hourly Power Load profile line plot comparing peak load shifting."""
        save_path = self.output_dir / "peak_load_comparison.png"
        fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

        horizon = Config.SCHEDULING_HORIZON_SLOTS
        opt_load = np.zeros(horizon)
        fcfs_load = np.zeros(horizon)

        for _, row in opt_df.iterrows():
            for t in range(int(row["Start_Slot"]), int(row["End_Slot"])):
                if t < horizon:
                    opt_load[t] += 15.0  # Approx active kW load

        for _, row in fcfs_df.iterrows():
            for t in range(int(row["Start_Slot"]), int(row["End_Slot"])):
                if t < horizon:
                    fcfs_load[t] += 15.0

        slots = np.arange(horizon)
        ax.plot(slots, fcfs_load, label="FCFS Baseline Load (kW)", color="#d62728", linestyle="--", linewidth=2)
        ax.plot(slots, opt_load, label="CP-SAT Optimized Load (kW)", color="#2ca02c", linewidth=2.2)

        # Highlight Peak Hours range
        ax.axvspan(32, 80, color="orange", alpha=0.15, label="Peak Tariff Window (08:00 - 20:00)")

        ax.set_title("Hourly Power Demand Profile & Peak Load Shifting", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Time Slot Index (15-min resolution)", fontsize=12)
        ax.set_ylabel("Aggregate Active Power (kW)", fontsize=12)
        ax.legend(fontsize=10, loc="upper right")
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")
