"""
Forecast Visualizer Module.
Generates publication-quality forecasting charts: Actual vs Predicted, Error Distribution,
Feature Importance, Residual Plot, and Time-Series Forecast Curves saved to outputs/forecasting.
"""

from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class ForecastVisualizer:
    """Class generating comprehensive visualization suite for energy demand forecasts."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Config.FORECAST_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="deep")
        plt.rcParams.update({"font.sans-serif": "DejaVu Sans", "font.family": "sans-serif"})

    def generate_all_plots(
        self,
        predictions_df: pd.DataFrame,
        feature_importance_df: pd.DataFrame,
        future_forecast_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Executes visualization pipeline generating all 5 required forecasting figures.

        Args:
            predictions_df: DataFrame containing test set predictions.
            feature_importance_df: DataFrame containing ranked feature importances.
            future_forecast_df: Optional DataFrame containing future predicted steps.
        """
        logger.info("Starting automated forecast visualization generation...")
        
        self.plot_actual_vs_predicted(predictions_df)
        self.plot_error_distribution(predictions_df)
        self.plot_feature_importance(feature_importance_df)
        self.plot_residual_plot(predictions_df)
        self.plot_timeseries_forecast_curve(predictions_df, future_forecast_df)

        logger.info(f"All forecast figures successfully saved to {self.output_dir}")

    def plot_actual_vs_predicted(self, df: pd.DataFrame) -> None:
        """Generates Actual vs Predicted line plot comparison over test period."""
        save_path = self.output_dir / "actual_vs_predicted.png"
        fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

        # Plot sample window for visual clarity if test dataset is large
        sample_df = df.iloc[:400] if len(df) > 400 else df

        ax.plot(sample_df["timestamp"], sample_df["actual_kWh"], label="Actual kWh", color="#1f77b4", linewidth=2.0, alpha=0.85)
        ax.plot(sample_df["timestamp"], sample_df["predicted_kWh"], label="Predicted kWh (XGBoost)", color="#d62728", linestyle="--", linewidth=1.8, alpha=0.9)

        ax.set_title("Energy Consumption Demand: Actual vs Predicted (XGBoost)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Timestamp", fontsize=12)
        ax.set_ylabel("Energy Usage (kWh)", fontsize=12)
        ax.legend(fontsize=11, loc="upper right")
        ax.grid(True, linestyle=":", alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_error_distribution(self, df: pd.DataFrame) -> None:
        """Generates histogram & KDE distribution plot of prediction residual errors."""
        save_path = self.output_dir / "error_distribution.png"
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        errors = df["residual_error"]
        sns.histplot(errors, kde=True, color="#2ca02c", bins=50, ax=ax)

        mean_err = errors.mean()
        std_err = errors.std()

        ax.axvline(0, color="black", linestyle="-", linewidth=1.2, label="Zero Error Line")
        ax.axvline(mean_err, color="red", linestyle="--", linewidth=1.5, label=f"Mean Error: {mean_err:.3f} kWh")

        ax.set_title("Prediction Residual Error Distribution (Actual - Predicted)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Residual Error (kWh)", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.legend(fontsize=10)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_feature_importance(self, fi_df: pd.DataFrame, top_n: int = 15) -> None:
        """Generates ranked horizontal bar chart of top N feature importances."""
        save_path = self.output_dir / "feature_importance.png"
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)

        top_fi = fi_df.head(top_n).sort_values(by="Importance", ascending=True)

        sns.barplot(x="Importance", y="Feature", data=top_fi, palette="Blues_r", ax=ax)
        
        for p in ax.patches:
            width = p.get_width()
            ax.annotate(
                f"{width:.4f}",
                (width, p.get_y() + p.get_height() / 2.0),
                ha="left",
                va="center",
                xytext=(5, 0),
                textcoords="offset points",
                fontsize=9,
            )

        ax.set_title(f"XGBoost Feature Importance Ranking (Top {top_n})", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Importance Score (Gain)", fontsize=12)
        ax.set_ylabel("Feature Name", fontsize=12)

        plt.tight_layout()
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_residual_plot(self, df: pd.DataFrame) -> None:
        """Generates Residuals vs Predicted Values scatter plot to check heteroscedasticity."""
        save_path = self.output_dir / "residual_plot.png"
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        sns.scatterplot(x="predicted_kWh", y="residual_error", data=df, alpha=0.4, color="#9467bd", ax=ax)
        ax.axhline(0, color="red", linestyle="--", linewidth=1.5, label="Zero Error Baseline")

        ax.set_title("Residual Error vs Predicted Values (Homoscedasticity Check)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Predicted Energy Usage (kWh)", fontsize=12)
        ax.set_ylabel("Residual Error (Actual - Predicted kWh)", fontsize=12)
        ax.legend(fontsize=10)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")

    def plot_timeseries_forecast_curve(
        self, df_test: pd.DataFrame, df_future: Optional[pd.DataFrame] = None
    ) -> None:
        """Generates detailed multi-day zoomed-in forecast comparison & future forecast curve."""
        save_path = self.output_dir / "timeseries_forecast_curve.png"
        fig, ax = plt.subplots(figsize=(15, 6), dpi=300)

        # Plot 3-day recent historical test window (96 * 3 = 288 steps)
        recent_test = df_test.iloc[-288:] if len(df_test) >= 288 else df_test

        ax.plot(recent_test["timestamp"], recent_test["actual_kWh"], label="Historical Actual kWh", color="#1f77b4", linewidth=2.0)
        ax.plot(recent_test["timestamp"], recent_test["predicted_kWh"], label="XGBoost Test Predictions", color="#ff7f0e", linestyle="--", linewidth=1.8)

        if df_future is not None and not df_future.empty:
            ax.plot(df_future["timestamp"], df_future["predicted_kWh"], label="Phase 3 Future Forecast (24h Ahead)", color="#2ca02c", linestyle="-.", linewidth=2.2, marker="o", markersize=3)
            ax.axvline(df_future["timestamp"].iloc[0], color="black", linestyle=":", linewidth=1.5, label="Forecast Horizon Boundary")

        ax.set_title("Multi-Day Zoomed Energy Forecast Curve & Phase 3 Horizon", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Timestamp", fontsize=12)
        ax.set_ylabel("Energy Usage (kWh)", fontsize=12)
        ax.legend(fontsize=11, loc="upper left")
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Saved: {save_path.name}")
