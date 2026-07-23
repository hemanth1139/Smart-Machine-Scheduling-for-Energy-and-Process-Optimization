"""
Dataset Summary Report Generator Module.
Generates comprehensive technical dataset documentation summarizing dimensions,
column descriptions, missingness, feature dtypes, statistics, target metrics, and correlation highlights.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class SummaryReporter:
    """Generates detailed markdown summary reports for raw and processed datasets."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def generate_summary_report(
        self,
        energy_df: pd.DataFrame,
        energy_eng_df: pd.DataFrame,
        job_df: pd.DataFrame,
        machine_df: pd.DataFrame,
        save_path: Optional[Path] = None,
    ) -> Path:
        """
        Builds and saves dataset_summary_report.md into outputs/reports.

        Args:
            energy_df: Cleaned Energy DataFrame.
            energy_eng_df: Engineered Energy DataFrame.
            job_df: Cleaned Job DataFrame.
            machine_df: Cleaned Machine DataFrame.
            save_path: Output report path.

        Returns:
            Path: Saved report file path.
        """
        if save_path is None:
            save_path = self.cfg.REPORTS_OUTPUT_DIR / "dataset_summary_report.md"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating detailed dataset summary report at: {save_path}")

        lines = [
            "# AI-Based Smart Machine Scheduling: Phase 1 Dataset Summary Report",
            "",
            "## 1. Project Overview & Foundation",
            "",
            "This report summarizes the foundational datasets processed during Phase 1 for ",
            "**AI-Based Smart Machine Scheduling for Energy & Process Optimization**.",
            "",
            "- **Target Forecasting Variable**: `Usage_kWh` (15-minute resolution industrial consumption)",
            "- **Scheduling Scope**: Job dispatching across industrial machines optimized for peak/off-peak power.",
            "",
            "---",
            "",
            "## 2. Dataset Dimensions Overview",
            "",
            "| Dataset Name | Raw Rows | Raw Columns | Processed/Engineered Columns | Primary Key / Index |",
            "|---|---|---|---|---|",
            f"| **Energy Consumption (UCI)** | {len(energy_df):,} | {len(energy_df.columns)} | {len(energy_eng_df.columns)} | `date` (Datetime) |",
            f"| **Jobs Specifications** | {len(job_df):,} | {len(job_df.columns)} | {len(job_df.columns)} | `Job_ID` |",
            f"| **Machine Specifications** | {len(machine_df):,} | {len(machine_df.columns)} | {len(machine_df.columns)} | `Machine_ID` |",
            "",
            "---",
            "",
            "## 3. Energy Dataset Features & Schema Description",
            "",
            "| Column Name | Data Type | Missing Count | Description / Role |",
            "|---|---|---|---|",
        ]

        # Column descriptions for energy dataset
        col_descriptions = {
            "date": "Timestamp (15-minute interval records)",
            "Usage_kWh": "Target variable: Active energy consumption in kilowatt-hours",
            "Lagging_Current_Reactive.Power_kVarh": "Lagging reactive energy in kVarh",
            "Leading_Current_Reactive_Power_kVarh": "Leading reactive energy in kVarh",
            "CO2(tCO2)": "Carbon dioxide emission equivalent in metric tons",
            "Lagging_Current_Power_Factor": "Power factor under lagging current (%)",
            "Leading_Current_Power_Factor": "Power factor under leading current (%)",
            "NSM": "Number of seconds elapsed from midnight",
            "WeekStatus": "Categorical indicator (Weekday vs Weekend)",
            "Day_of_week": "Day name (Monday to Sunday)",
            "Load_Type": "Plant electrical load classification (Light_Load, Medium_Load, Maximum_Load)",
        }

        for col in energy_df.columns:
            dtype = str(energy_df[col].dtype)
            missing = int(energy_df[col].isnull().sum())
            desc = col_descriptions.get(col, "Feature column")
            lines.append(f"| `{col}` | `{dtype}` | {missing} | {desc} |")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Target Variable Analysis (`Usage_kWh`)",
            "",
        ])

        target = "Usage_kWh" if "Usage_kWh" in energy_df.columns else energy_df.columns[1]
        target_s = energy_df[target]
        mean_val = float(target_s.mean())
        std_val = float(target_s.std())
        min_val = float(target_s.min())
        q25_val = float(target_s.quantile(0.25))
        q50_val = float(target_s.median())
        q75_val = float(target_s.quantile(0.75))
        max_val = float(target_s.max())

        lines.extend([
            f"- **Mean**: {mean_val:.2f} kWh",
            f"- **Standard Deviation**: {std_val:.2f} kWh",
            f"- **Minimum**: {min_val:.2f} kWh",
            f"- **25th Percentile**: {q25_val:.2f} kWh",
            f"- **Median (50%)**: {q50_val:.2f} kWh",
            f"- **75th Percentile**: {q75_val:.2f} kWh",
            f"- **Maximum**: {max_val:.2f} kWh",
            "",
            "### Target Usage by Load Type",
            "",
            "| Load Type | Mean Usage (kWh) | Min Usage | Max Usage | Record Count |",
            "|---|---|---|---|---|",
        ])

        if "Load_Type" in energy_df.columns:
            grp = energy_df.groupby("Load_Type")[target].agg(["mean", "min", "max", "count"])
            for lt, row in grp.iterrows():
                lines.append(
                    f"| `{lt}` | {row['mean']:.2f} | {row['min']:.2f} | {row['max']:.2f} | {int(row['count']):,} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 5. Correlation Analysis Highlights",
            "",
            "Linear correlation coefficients with target variable `Usage_kWh`:",
            "",
            "| Feature | Correlation with `Usage_kWh` | Interpretation |",
            "|---|---|---|",
        ])

        numeric_df = energy_df.select_dtypes(include=[np.number])
        if target in numeric_df.columns:
            corrs = numeric_df.corr()[target].drop(target).sort_values(ascending=False)
            for feat, corr_val in corrs.items():
                interp = (
                    "Strong Positive" if corr_val > 0.6
                    else "Moderate Positive" if corr_val > 0.3
                    else "Negligible" if abs(corr_val) <= 0.3
                    else "Moderate Negative" if corr_val > -0.6
                    else "Strong Negative"
                )
                lines.append(f"| `{feat}` | {corr_val:.4f} | {interp} |")

        lines.extend([
            "",
            "---",
            "",
            "## 6. Engineered Features Summary (Phase 2 Readiness)",
            "",
            "The following time-series feature sets were generated for downstream forecasting:",
            "",
            "- **Temporal Features**: `hour`, `day`, `month`, `day_of_week`, `quarter`, `day_of_year`, `is_weekend`",
            "- **Cyclical Encodings**: `hour_sin`, `hour_cos`, `month_sin`, `month_cos`",
            "- **Lagged Target Features**: `Usage_kWh_lag_1`, `Usage_kWh_lag_2`, `Usage_kWh_lag_4`, `Usage_kWh_lag_96`",
            "- **Rolling Window Statistics**: `Usage_kWh_rolling_mean_4`, `Usage_kWh_rolling_std_4`, `Usage_kWh_rolling_mean_96`, `Usage_kWh_rolling_std_96`",
            "- **Exponential Moving Averages**: `Usage_kWh_ewma_4`",
            "",
            "---",
            "",
            "## 7. Synthetic Job & Machine Specifications",
            "",
            "### Machine Specs Overview",
            "| Machine ID | Machine Type | Idle Power (kW) | Active Power (kW) | Changeover Time (min) | Available Hours |",
            "|---|---|---|---|---|---|",
        ])

        for _, row in machine_df.iterrows():
            lines.append(
                f"| `{row.get('Machine_ID', '')}` | `{row.get('Machine_Type', '')}` | "
                f"{row.get('Idle_Power_kW', '')} | {row.get('Active_Power_kW', '')} | "
                f"{row.get('Changeover_Time_min', '')} | {row.get('Available_From', '')} to {row.get('Available_To', '')} |"
            )

        lines.extend([
            "",
            "### Job Specs Summary",
            f"- **Total Jobs**: {len(job_df)} jobs",
            f"- **Average Duration**: {job_df['Duration_min'].mean():.1f} minutes",
            f"- **Priority Breakdown**: High ({sum(job_df['Priority'] == 'High')}), Medium ({sum(job_df['Priority'] == 'Medium')}), Low ({sum(job_df['Priority'] == 'Low')})",
            "",
            "---",
            "",
            "**Status**: Phase 1 foundation complete. Cleaned & feature-engineered datasets ready for Phase 2 energy forecasting models.",
        ])

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Summary report successfully exported to: {save_path}")
        return save_path
