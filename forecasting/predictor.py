"""
Forecasting Predictor & Future Time-Slot Generator.
Generates predictions for test evaluation set and predicts multi-step future time slots for Phase 3 scheduling.
"""

from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import numpy as np

from forecasting.base_model import BaseForecaster
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class ForecastingPredictor:
    """Predictor class managing test prediction generation and future energy forecasting."""

    def __init__(self, forecaster: BaseForecaster, cfg: Config = config):
        self.forecaster = forecaster
        self.cfg = cfg

    def predict_test_set(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        dates_test: pd.Series,
        save_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """
        Generates predictions for test set and exports structured prediction DataFrame to CSV.

        Args:
            X_test: Test set feature DataFrame.
            y_test: Test set true target Series.
            dates_test: Test set timestamp Series.
            save_path: Output CSV file path.

        Returns:
            pd.DataFrame: Structured prediction results DataFrame.
        """
        if save_path is None:
            save_path = self.cfg.PREDICTIONS_CSV_PATH

        save_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating energy demand predictions for {len(X_test)} test samples...")
        y_pred = self.forecaster.predict(X_test)

        residuals = y_test.values - y_pred
        abs_errors = np.abs(residuals)
        pct_errors = np.where(y_test.values > 1e-5, (abs_errors / (y_test.values + 1e-5)) * 100.0, 0.0)

        results_df = pd.DataFrame({
            "timestamp": dates_test.values,
            "actual_kWh": y_test.values,
            "predicted_kWh": y_pred,
            "residual_error": residuals,
            "abs_error": abs_errors,
            "pct_error": np.round(pct_errors, 2),
        })

        results_df.to_csv(save_path, index=False)
        logger.info(f"Test predictions exported to: {save_path}")
        return results_df

    def forecast_future_horizon(
        self,
        last_known_row: pd.DataFrame,
        last_timestamp: pd.Timestamp,
        steps: int = Config.FUTURE_FORECAST_STEPS,
        save_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """
        Generates multi-step future time-slot energy predictions for downstream Phase 3 machine scheduling.

        Args:
            last_known_row: Last feature row available in sequence.
            last_timestamp: Datetime of last observed sequence element.
            steps: Number of future 15-minute intervals to forecast (default 96 steps = 24 hours).
            save_path: Output path for future forecast CSV.

        Returns:
            pd.DataFrame: Future predictions with timestamp, predicted_kWh, hour, and day_of_week.
        """
        if save_path is None:
            save_path = self.cfg.FUTURE_FORECAST_CSV_PATH

        save_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating future energy demand forecast for next {steps} time slots (24 hours)...")

        future_dates = [
            last_timestamp + pd.Timedelta(minutes=15 * (i + 1)) for i in range(steps)
        ]

        # Construct future feature frame dynamically based on expected feature schema
        curr_row = last_known_row.copy().iloc[[0]]
        future_preds = []

        for i, f_date in enumerate(future_dates):
            # Update temporal features for step
            if "hour" in curr_row.columns:
                curr_row["hour"] = f_date.hour
            if "day" in curr_row.columns:
                curr_row["day"] = f_date.day
            if "month" in curr_row.columns:
                curr_row["month"] = f_date.month
            if "day_of_week" in curr_row.columns:
                curr_row["day_of_week"] = f_date.dayofweek
            if "is_weekend" in curr_row.columns:
                curr_row["is_weekend"] = 1 if f_date.dayofweek in [5, 6] else 0
            if "hour_sin" in curr_row.columns:
                curr_row["hour_sin"] = np.sin(2 * np.pi * f_date.hour / 24.0)
            if "hour_cos" in curr_row.columns:
                curr_row["hour_cos"] = np.cos(2 * np.pi * f_date.hour / 24.0)

            pred_val = float(self.forecaster.predict(curr_row)[0])
            future_preds.append(pred_val)

            # Shift lag_1 with predicted value for next iteration if present
            lag_1_col = f"{self.cfg.ENERGY_TARGET_COL}_lag_1"
            if lag_1_col in curr_row.columns:
                curr_row[lag_1_col] = pred_val

        future_df = pd.DataFrame({
            "timestamp": future_dates,
            "predicted_kWh": np.round(future_preds, 3),
            "hour": [d.hour for d in future_dates],
            "day_of_week": [d.strftime("%A") for d in future_dates],
            "is_weekend": [1 if d.dayofweek in [5, 6] else 0 for d in future_dates],
        })

        future_df.to_csv(save_path, index=False)
        logger.info(f"Future {steps}-step forecast exported to: {save_path}")
        return future_df
