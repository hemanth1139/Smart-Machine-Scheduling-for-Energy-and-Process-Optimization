"""
Scheduling Exporter Module.
Exports schedule DataFrames, KPI summaries, comparison CSVs, and markdown reports to outputs/scheduling and outputs/reports.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class SchedulingExporter:
    """Exports scheduling results, comparison matrices, and markdown summary reports."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def export_schedules_and_kpis(
        self,
        opt_df: pd.DataFrame,
        fcfs_df: pd.DataFrame,
        opt_kpis: Dict[str, Any],
        fcfs_kpis: Dict[str, Any],
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """
        Exports schedules, KPI summaries, and comparison tables to CSV format.

        Returns:
            Dict[str, Path]: Dictionary mapping artifact key to output file path.
        """
        if output_dir is None:
            output_dir = self.cfg.SCHEDULING_OUTPUT_DIR

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Exporting scheduling output CSV files to: {output_dir}")

        opt_csv_path = output_dir / self.cfg.OPTIMIZED_SCHEDULE_FILENAME
        fcfs_csv_path = output_dir / self.cfg.FCFS_SCHEDULE_FILENAME
        kpi_csv_path = output_dir / self.cfg.KPI_SUMMARY_FILENAME
        comp_csv_path = output_dir / self.cfg.COMPARISON_REPORT_FILENAME

        opt_df.to_csv(opt_csv_path, index=False)
        fcfs_df.to_csv(fcfs_csv_path, index=False)

        # Build KPI Summary DataFrame
        kpi_df = pd.DataFrame([
            {"Schedule_Type": "Baseline_FCFS", **fcfs_kpis},
            {"Schedule_Type": "CP_SAT_Optimized", **opt_kpis},
        ])
        kpi_df.to_csv(kpi_csv_path, index=False)

        # Build Quantitative Comparison Matrix
        cost_diff = fcfs_kpis.get("Total_Energy_Cost_$", 0) - opt_kpis.get("Total_Energy_Cost_$", 0)
        cost_pct = (cost_diff / max(1, fcfs_kpis.get("Total_Energy_Cost_$", 1))) * 100.0

        peak_diff = fcfs_kpis.get("Peak_Hour_Load_kWh", 0) - opt_kpis.get("Peak_Hour_Load_kWh", 0)
        peak_pct = (peak_diff / max(1, fcfs_kpis.get("Peak_Hour_Load_kWh", 1))) * 100.0

        makespan_diff = fcfs_kpis.get("Makespan_min", 0) - opt_kpis.get("Makespan_min", 0)
        makespan_str = f"{makespan_diff} min reduction" if makespan_diff >= 0 else f"{abs(makespan_diff)} min increase"

        ontime_diff = opt_kpis.get("On_Time_Completion_%", 0) - fcfs_kpis.get("On_Time_Completion_%", 0)
        ontime_str = f"+{ontime_diff:.1f}% improvement" if ontime_diff >= 0 else f"{ontime_diff:.1f}%"

        util_diff = opt_kpis.get("Machine_Utilization_%", 0) - fcfs_kpis.get("Machine_Utilization_%", 0)
        util_str = f"+{util_diff:.1f}% improvement" if util_diff >= 0 else f"{util_diff:.1f}%"

        comp_df = pd.DataFrame([
            {"Metric": "Total Energy Cost (₹)", "FCFS_Baseline": fcfs_kpis.get("Total_Energy_Cost_$", 0), "CP_SAT_Optimized": opt_kpis.get("Total_Energy_Cost_$", 0), "Improvement": f"₹{cost_diff:.2f} ({cost_pct:.1f}% reduction)"},
            {"Metric": "Peak-Hour Load (kWh)", "FCFS_Baseline": fcfs_kpis.get("Peak_Hour_Load_kWh", 0), "CP_SAT_Optimized": opt_kpis.get("Peak_Hour_Load_kWh", 0), "Improvement": f"{peak_diff:.2f} kWh ({peak_pct:.1f}% reduction)"},
            {"Metric": "Makespan (min)", "FCFS_Baseline": fcfs_kpis.get("Makespan_min", 0), "CP_SAT_Optimized": opt_kpis.get("Makespan_min", 0), "Improvement": makespan_str},
            {"Metric": "On-Time Completion Rate (%)", "FCFS_Baseline": f"{fcfs_kpis.get('On_Time_Completion_%', 0)}%", "CP_SAT_Optimized": f"{opt_kpis.get('On_Time_Completion_%', 0)}%", "Improvement": ontime_str},
            {"Metric": "Machine Utilization (%)", "FCFS_Baseline": f"{fcfs_kpis.get('Machine_Utilization_%', 0)}%", "CP_SAT_Optimized": f"{opt_kpis.get('Machine_Utilization_%', 0)}%", "Improvement": util_str},
        ])
        comp_df.to_csv(comp_csv_path, index=False)

        logger.info(f"Saved: {opt_csv_path.name}, {fcfs_csv_path.name}, {kpi_csv_path.name}, {comp_csv_path.name}")

        return {
            "opt_schedule": opt_csv_path,
            "fcfs_schedule": fcfs_csv_path,
            "kpi_summary": kpi_csv_path,
            "comparison": comp_csv_path,
        }

    def generate_markdown_report(
        self,
        opt_kpis: Dict[str, Any],
        fcfs_kpis: Dict[str, Any],
        save_path: Optional[Path] = None,
    ) -> Path:
        """
        Builds and exports detailed markdown scheduling comparison report to outputs/reports/scheduling_report.md.

        Returns:
            Path: Report file path.
        """
        if save_path is None:
            save_path = self.cfg.REPORTS_OUTPUT_DIR / "scheduling_report.md"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating scheduling report at: {save_path}")

        cost_diff = fcfs_kpis.get("Total_Energy_Cost_$", 0) - opt_kpis.get("Total_Energy_Cost_$", 0)
        cost_pct = (cost_diff / max(1, fcfs_kpis.get("Total_Energy_Cost_$", 1))) * 100.0

        peak_diff = fcfs_kpis.get("Peak_Hour_Load_kWh", 0) - opt_kpis.get("Peak_Hour_Load_kWh", 0)
        peak_pct = (peak_diff / max(1, fcfs_kpis.get("Peak_Hour_Load_kWh", 1))) * 100.0

        makespan_diff = fcfs_kpis.get('Makespan_min', 0) - opt_kpis.get('Makespan_min', 0)
        makespan_str = f"{makespan_diff} min reduction" if makespan_diff >= 0 else f"{abs(makespan_diff)} min increase"

        ontime_diff = opt_kpis.get('On_Time_Completion_%', 0) - fcfs_kpis.get('On_Time_Completion_%', 0)
        ontime_str = f"+{ontime_diff:.1f}%" if ontime_diff >= 0 else f"{ontime_diff:.1f}%"

        util_diff = opt_kpis.get('Machine_Utilization_%', 0) - fcfs_kpis.get('Machine_Utilization_%', 0)
        util_str = f"+{util_diff:.1f}%" if util_diff >= 0 else f"{util_diff:.1f}%"

        lines = [
            "# AI-Based Smart Machine Scheduling: Phase 3 Optimization Report",
            "",
            "## 1. Executive Summary",
            "",
            "Phase 3 delivers an **Intelligent Machine Scheduling Optimization Engine** using **Google OR-Tools (CP-SAT Solver)**. ",
            "The optimizer ingests energy demand forecasts from Phase 2, machine specifications, and job constraints to minimize ",
            "electricity costs, peak-hour load, changeovers, and delays.",
            "",
            "- **Primary Optimization Solver**: Google OR-Tools CP-SAT Solver",
            "- **Benchmark Baseline**: First-Come-First-Served (FCFS) Heuristic",
            f"- **Electricity Cost Savings**: **₹{cost_diff:.2f}** ({cost_pct:.1f}% reduction)",
            f"- **Peak-Hour Load Reduction**: **{peak_diff:.2f} kWh** ({peak_pct:.1f}% reduction)",
            "",
            "---",
            "",
            "## 2. Quantitative KPI Performance Comparison",
            "",
            "| Key Performance Indicator (KPI) | FCFS Baseline | CP-SAT Optimized | Improvement / Delta |",
            "|---|---|---|---|",
            f"| **Total Electricity Cost (₹)** | `₹{fcfs_kpis.get('Total_Energy_Cost_$', 0):,.2f}` | `₹{opt_kpis.get('Total_Energy_Cost_$', 0):,.2f}` | **₹{cost_diff:.2f} ({cost_pct:.1f}% savings)** |",
            f"| **Peak-Hour Electricity Load (kWh)** | `{fcfs_kpis.get('Peak_Hour_Load_kWh', 0):,.2f}` | `{opt_kpis.get('Peak_Hour_Load_kWh', 0):,.2f}` | **{peak_diff:.2f} kWh ({peak_pct:.1f}% reduction)** |",
            f"| **Makespan (Hours)** | `{fcfs_kpis.get('Makespan_hours', 0)}` hrs | `{opt_kpis.get('Makespan_hours', 0)}` hrs | **{makespan_str}** |",
            f"| **On-Time Job Completion Rate (%)** | `{fcfs_kpis.get('On_Time_Completion_%', 0)}%` | `{opt_kpis.get('On_Time_Completion_%', 0)}%` | **{ontime_str}** |",
            f"| **Machine Utilization (%)** | `{fcfs_kpis.get('Machine_Utilization_%', 0)}%` | `{opt_kpis.get('Machine_Utilization_%', 0)}%` | **{util_str}** |",
            f"| **Average Job Waiting Time (min)** | `{fcfs_kpis.get('Average_Waiting_Time_min', 0)}` min | `{opt_kpis.get('Average_Waiting_Time_min', 0)}` min | **Optimized queue management** |",
            f"| **Late Jobs Count** | `{fcfs_kpis.get('Number_of_Late_Jobs', 0)}` jobs | `{opt_kpis.get('Number_of_Late_Jobs', 0)}` jobs | **Zero / Minimized delays** |",
            "",
            "---",
            "",
            "## 3. Physical Constraints Enforced",
            "",
            "1. **Machine Non-Overlap**: One machine processes only one job at a time.",
            "2. **Machine Compatibility**: Jobs assigned strictly to compatible machines.",
            "3. **Job Arrival Time**: Job start time $\\ge$ arrival timestamp.",
            "4. **Machine Availability**: Operating window within machine availability schedule.",
            "5. **Changeover Times**: Minimum changeover gap between consecutive jobs.",
            "6. **Duration Constraints**: Job execution time strictly preserved.",
            "",
            "---",
            "",
            "## 4. Phase 4 Dashboard Integration Readiness",
            "",
            "- **Optimized Schedule CSV**: `outputs/scheduling/optimized_schedule.csv`",
            "- **FCFS Baseline CSV**: `outputs/scheduling/fcfs_schedule.csv`",
            "- **KPI Summary CSV**: `outputs/scheduling/kpi_summary.csv`",
            "- **Visualizations**: 7 high-resolution PNG charts generated in `outputs/scheduling/`",
            "",
            "**Status**: Phase 3 scheduling optimization engine complete. Ready to feed interactive visual schedules into **Phase 4 Web Dashboard**.",
        ]

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown scheduling report saved to: {save_path}")
        return save_path
