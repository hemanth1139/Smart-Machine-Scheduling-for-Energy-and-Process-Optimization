"""
Exploratory Data Analysis (EDA) Utility Module.
Generates and saves publication-quality visualization charts into outputs/eda.
"""

from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from config.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class EDAGenerator:
    """Class responsible for generating and saving automated EDA visualizations."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Config.EDA_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="muted")
        plt.rcParams.update({"font.sans-serif": "DejaVu Sans", "font.family": "sans-serif"})

    def generate_all_plots(
        self,
        energy_df: pd.DataFrame,
        jobs_df: Optional[pd.DataFrame] = None,
        machines_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Executes complete automated EDA generation pipeline across all datasets.

        Args:
            energy_df: Cleaned/Engineered Energy Consumption Dataframe.
            jobs_df: Optional Jobs Dataframe.
            machines_df: Optional Machine Specifications Dataframe.
        """
        logger.info("Starting automated EDA plot generation...")
        
        self.plot_energy_distribution(energy_df)
        self.plot_correlation_heatmap(energy_df)
        self.plot_load_type_distribution(energy_df)
        self.plot_weekday_vs_weekend(energy_df)
        self.plot_feature_distributions(energy_df)
        self.plot_time_of_day_usage(energy_df)

        if jobs_df is not None and machines_df is not None:
            self.plot_jobs_and_machines(jobs_df, machines_df)

        logger.info(f"All EDA visualizations successfully saved to {self.output_dir}")

    def plot_energy_distribution(self, df: pd.DataFrame) -> None:
        """Generates histogram and KDE plot of target energy consumption (Usage_kWh)."""
        save_path = self.output_dir / "energy_distribution.png"
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        target_col = "Usage_kWh" if "Usage_kWh" in df.columns else "usage_kwh"
        if target_col not in df.columns:
            logger.warning(f"Target column '{target_col}' not found for energy distribution plot.")
            return

        sns.histplot(df[target_col], kde=True, color="#1f77b4", bins=50, ax=ax)
        
        mean_val = df[target_col].mean()
        median_val = df[target_col].median()
        
        ax.axvline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mean: {mean_val:.2f} kWh")
        ax.axvline(median_val, color="green", linestyle="-.", linewidth=1.5, label=f"Median: {median_val:.2f} kWh")

        ax.set_title("Energy Consumption Distribution (Usage_kWh)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Energy Usage (kWh)", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.legend(fontsize=10)
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_correlation_heatmap(self, df: pd.DataFrame) -> None:
        """Generates correlation heatmap for numerical power & energy metrics."""
        save_path = self.output_dir / "correlation_heatmap.png"
        numeric_df = df.select_dtypes(include=[np.number])

        # Exclude synthetic lag / rolling features for cleaner core correlation
        core_cols = [
            c for c in numeric_df.columns 
            if not ("lag" in c.lower() or "rolling" in c.lower() or "sin" in c.lower() or "cos" in c.lower())
        ]
        corr_matrix = numeric_df[core_cols].corr()

        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".2f",
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax,
        )
        ax.set_title("Correlation Heatmap of Energy & Electrical Metrics", fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_load_type_distribution(self, df: pd.DataFrame) -> None:
        """Generates distribution count plot and proportion pie chart for Load Type."""
        save_path = self.output_dir / "load_type_distribution.png"
        col = "Load_Type" if "Load_Type" in df.columns else "load_type"
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found for Load Type plot.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)
        
        counts = df[col].value_counts()
        colors = ["#2ca02c", "#ff7f0e", "#d62728"][: len(counts)]

        # Bar chart
        sns.barplot(x=counts.index, y=counts.values, palette=colors, ax=ax1)
        ax1.set_title("Load Type Frequency Counts", fontsize=12, fontweight="bold")
        ax1.set_xlabel("Load Type", fontsize=11)
        ax1.set_ylabel("Count", fontsize=11)

        for p in ax1.patches:
            ax1.annotate(
                f"{int(p.get_height()):,}",
                (p.get_x() + p.get_width() / 2.0, p.get_height()),
                ha="center",
                va="center",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=10,
            )

        # Pie chart
        ax2.pie(counts.values, labels=counts.index, autopct="%1.1f%%", colors=colors, startangle=140, explode=[0.05]*len(counts))
        ax2.set_title("Load Type Proportion Breakdown", fontsize=12, fontweight="bold")

        plt.suptitle("Load Type Distribution Analysis", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_weekday_vs_weekend(self, df: pd.DataFrame) -> None:
        """Generates comparative boxplot & hourly profile for Weekday vs Weekend energy consumption."""
        save_path = self.output_dir / "weekday_vs_weekend.png"
        target = "Usage_kWh" if "Usage_kWh" in df.columns else "usage_kwh"
        week_col = "WeekStatus" if "WeekStatus" in df.columns else "week_status"

        if target not in df.columns or week_col not in df.columns:
            logger.warning(f"Required columns missing for Weekday vs Weekend plot.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

        # Boxplot comparison
        sns.boxplot(x=week_col, y=target, data=df, palette="Set2", ax=ax1, showmeans=True)
        ax1.set_title("Energy Usage Distribution: Weekday vs Weekend", fontsize=12, fontweight="bold")
        ax1.set_xlabel("Day Status", fontsize=11)
        ax1.set_ylabel("Usage (kWh)", fontsize=11)

        # Hourly average profile by WeekStatus
        if "hour" in df.columns:
            hourly_status = df.groupby(["hour", week_col])[target].mean().reset_index()
            sns.lineplot(x="hour", y=target, hue=week_col, data=hourly_status, marker="o", ax=ax2, palette="Set2")
            ax2.set_title("Average Hourly Profile: Weekday vs Weekend", fontsize=12, fontweight="bold")
            ax2.set_xlabel("Hour of Day", fontsize=11)
            ax2.set_ylabel("Mean Usage (kWh)", fontsize=11)
            ax2.set_xticks(range(0, 24, 2))

        plt.suptitle("Weekday vs Weekend Energy Consumption Analysis", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_feature_distributions(self, df: pd.DataFrame) -> None:
        """Generates grid of boxplots for power factors and reactive powers."""
        save_path = self.output_dir / "feature_distributions.png"
        feature_cols = [
            c for c in [
                "Lagging_Current_Reactive.Power_kVarh",
                "Leading_Current_Reactive_Power_kVarh",
                "Lagging_Current_Power_Factor",
                "Leading_Current_Power_Factor",
                "CO2(tCO2)",
            ] if c in df.columns
        ]

        if not feature_cols:
            return

        n_cols = len(feature_cols)
        fig, axes = plt.subplots(2, (n_cols + 1) // 2, figsize=(14, 8), dpi=300)
        axes = axes.flatten()

        for idx, col in enumerate(feature_cols):
            sns.histplot(df[col], kde=True, ax=axes[idx], color="#9467bd")
            axes[idx].set_title(col, fontsize=10, fontweight="bold")
            axes[idx].set_xlabel("")
            axes[idx].set_ylabel("Count", fontsize=9)

        # Hide any unused axes
        for j in range(len(feature_cols), len(axes)):
            fig.delaxes(axes[j])

        plt.suptitle("Electrical & Power Quality Feature Distributions", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_time_of_day_usage(self, df: pd.DataFrame) -> None:
        """Generates hourly energy usage pattern plot (mean, median, std envelope)."""
        save_path = self.output_dir / "time_of_day_usage.png"
        target = "Usage_kWh" if "Usage_kWh" in df.columns else "usage_kwh"

        if target not in df.columns:
            return

        # Infer hour if not already computed
        if "hour" in df.columns:
            hour_col = df["hour"]
        elif "date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["date"]):
            hour_col = df["date"].dt.hour
        else:
            return

        df_temp = df.copy()
        df_temp["_temp_hour"] = hour_col

        hourly_stats = df_temp.groupby("_temp_hour")[target].agg(["mean", "median", "std"]).reset_index()

        fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
        ax.plot(hourly_stats["_temp_hour"], hourly_stats["mean"], label="Mean Usage", color="#1f77b4", linewidth=2.5, marker="o")
        ax.plot(hourly_stats["_temp_hour"], hourly_stats["median"], label="Median Usage", color="#ff7f0e", linestyle="--", linewidth=2, marker="s")
        
        # Standard deviation band
        ax.fill_between(
            hourly_stats["_temp_hour"],
            hourly_stats["mean"] - hourly_stats["std"],
            hourly_stats["mean"] + hourly_stats["std"],
            color="#1f77b4",
            alpha=0.15,
            label="± 1 Std Dev",
        )

        ax.set_title("Time-of-Day Energy Consumption Profile (Hourly)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Hour of Day (0 - 23)", fontsize=12)
        ax.set_ylabel("Usage (kWh)", fontsize=12)
        ax.set_xticks(range(0, 24))
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_jobs_and_machines(self, jobs_df: pd.DataFrame, machines_df: pd.DataFrame) -> None:
        """Generates EDA visualizations for Job specifications and Machine metrics."""
        save_path = self.output_dir / "jobs_and_machines_eda.png"

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10), dpi=300)

        # 1. Job Duration Distribution
        if "Duration_min" in jobs_df.columns:
            sns.histplot(jobs_df["Duration_min"], kde=True, color="#2ca02c", ax=ax1)
            ax1.set_title("Job Duration Distribution (minutes)", fontsize=11, fontweight="bold")
            ax1.set_xlabel("Duration (min)")

        # 2. Job Priority Counts
        if "Priority" in jobs_df.columns:
            sns.countplot(x="Priority", data=jobs_df, palette="viridis", ax=ax2, order=["High", "Medium", "Low"])
            ax2.set_title("Job Count by Priority Level", fontsize=11, fontweight="bold")

        # 3. Machine Power Profile (Idle vs Active)
        if "Idle_Power_kW" in machines_df.columns and "Active_Power_kW" in machines_df.columns:
            m_plot = machines_df.melt(
                id_vars=["Machine_ID"],
                value_vars=["Idle_Power_kW", "Active_Power_kW"],
                var_name="Power_Mode",
                value_name="Power_kW",
            )
            sns.barplot(x="Machine_ID", y="Power_kW", hue="Power_Mode", data=m_plot, ax=ax3, palette="magma")
            ax3.set_title("Machine Power Profile (Idle vs Active kW)", fontsize=11, fontweight="bold")
            ax3.tick_params(axis="x", rotation=45)

        # 4. Machine Types distribution
        if "Machine_Type" in machines_df.columns:
            sns.countplot(x="Machine_Type", data=machines_df, palette="crest", ax=ax4)
            ax4.set_title("Machine Inventory by Type", fontsize=11, fontweight="bold")
            ax4.tick_params(axis="x", rotation=45)

        plt.suptitle("Job & Machine Synthetic Dataset Overview", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")
