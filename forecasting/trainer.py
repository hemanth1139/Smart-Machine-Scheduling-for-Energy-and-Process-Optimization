"""
Forecasting Trainer Module.
Orchestrates model fitting, validation evaluation, and persistence.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from forecasting.base_model import BaseForecaster
from forecasting.xgb_model import XGBoostForecaster
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class ForecastingTrainer:
    """Trainer class overseeing energy forecasting model training and artifact export."""

    def __init__(
        self,
        forecaster: Optional[BaseForecaster] = None,
        cfg: Config = config,
    ):
        self.cfg = cfg
        self.forecaster = forecaster if forecaster is not None else XGBoostForecaster(cfg.XGB_HYPERPARAMETERS)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        model_save_path: Optional[Path] = None,
    ) -> BaseForecaster:
        """
        Executes model training pipeline and saves trained model artifact to disk.

        Args:
            X_train: Training feature DataFrame.
            y_train: Training target Series.
            X_val: Optional validation feature DataFrame.
            y_val: Optional validation target Series.
            model_save_path: Optional output path for model checkpoint.

        Returns:
            BaseForecaster: Fitted model instance.
        """
        if model_save_path is None:
            model_save_path = self.cfg.MODEL_OUTPUT_PATH

        logger.info("==================================================")
        logger.info("Starting Energy Demand Forecasting Model Training")
        logger.info("==================================================")

        # Fit model
        self.forecaster.fit(X_train, y_train, X_val=X_val, y_val=y_val)

        # Save model checkpoint
        self.forecaster.save(model_save_path)
        logger.info(f"Model training successfully completed. Saved to: {model_save_path}")

        return self.forecaster
