"""
Forecasting Model Evaluator Module.
Calculates statistical regression metrics (MAE, RMSE, R2, MAPE) for model performance evaluation.
"""

from typing import Dict, Any, Union
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from utils.logger import get_logger

logger = get_logger(__name__)


class ForecastingEvaluator:
    """Evaluates forecasting model predictions against ground truth target values."""

    @staticmethod
    def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-5) -> float:
        """
        Computes Mean Absolute Percentage Error (MAPE) safely avoiding division by zero.

        Args:
            y_true: True values.
            y_pred: Predicted values.
            epsilon: Small scalar constant to prevent zero division.

        Returns:
            float: MAPE percentage (e.g. 5.23 for 5.23%).
        """
        y_true, y_pred = np.array(y_true), np.array(y_pred)
        # Filter near-zero true values to avoid infinite percentage spikes
        mask = np.abs(y_true) > epsilon
        if not np.any(mask):
            return 0.0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / (y_true[mask] + epsilon))) * 100.0
        return float(mape)

    def evaluate(
        self, y_true: Union[pd.Series, np.ndarray], y_pred: Union[pd.Series, np.ndarray]
    ) -> Dict[str, float]:
        """
        Calculates MAE, RMSE, R² Score, and MAPE regression performance metrics.

        Args:
            y_true: Ground truth target series or vector.
            y_pred: Predicted target series or vector.

        Returns:
            Dict[str, float]: Dictionary containing computed metrics.
        """
        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)

        mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
        rmse = float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
        r2 = float(r2_score(y_true_arr, y_pred_arr))
        mape = float(self.calculate_mape(y_true_arr, y_pred_arr))

        metrics = {
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "R2": round(r2, 4),
            "MAPE": round(mape, 4),
        }

        logger.info("--------------------------------------------------")
        logger.info("ENERGY DEMAND FORECASTING MODEL EVALUATION RESULTS:")
        logger.info(f"  • MAE  (Mean Absolute Error):      {metrics['MAE']} kWh")
        logger.info(f"  • RMSE (Root Mean Squared Error):  {metrics['RMSE']} kWh")
        logger.info(f"  • R²   (Coefficient of Determ.):   {metrics['R2']}")
        logger.info(f"  • MAPE (Mean Abs Pct Error):       {metrics['MAPE']}%")
        logger.info("--------------------------------------------------")

        return metrics
