"""
XGBoost Regressor Forecaster Module.
Implements the primary machine learning regressor for 15-minute energy demand forecasting.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional
import xgboost as xgb
import pandas as pd
import numpy as np
import joblib

from forecasting.base_model import BaseForecaster
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class XGBoostForecaster(BaseForecaster):
    """XGBoost Regressor wrapper implementing BaseForecaster interface."""

    def __init__(self, hyperparams: Optional[Dict[str, Any]] = None):
        self.params = hyperparams if hyperparams is not None else Config.XGB_HYPERPARAMETERS.copy()
        self.model: Optional[xgb.XGBRegressor] = None

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Union[pd.DataFrame, None] = None,
        y_val: Union[pd.Series, None] = None,
    ) -> "XGBoostForecaster":
        """
        Fits XGBoost Regressor with early stopping if validation set is supplied.

        Args:
            X_train: Training feature matrix.
            y_train: Training target series.
            X_val: Optional validation feature matrix.
            y_val: Optional validation target series.

        Returns:
            XGBoostForecaster: Fitted model instance.
        """
        logger.info(f"Initializing XGBoost Regressor with parameters: {self.params}")
        
        # Instantiate XGBRegressor
        self.model = xgb.XGBRegressor(**self.params)

        fit_params: Dict[str, Any] = {}
        if X_val is not None and y_val is not None:
            fit_params["eval_set"] = [(X_train, y_train), (X_val, y_val)]
            fit_params["verbose"] = 100  # Print progress every 100 iterations

        logger.info(f"Fitting XGBoost model on {len(X_train)} samples...")
        self.model.fit(X_train, y_train, **fit_params)
        logger.info("XGBoost model training completed successfully.")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generates predictions using fitted XGBoost model.

        Args:
            X: Input feature DataFrame.

        Returns:
            np.ndarray: Predicted energy values (Usage_kWh).

        Raises:
            ValueError: If model is not trained prior to calling predict.
        """
        if self.model is None:
            error_msg = "Model has not been trained yet. Call fit() or load() first."
            logger.error(error_msg)
            raise ValueError(error_msg)

        predictions = self.model.predict(X)
        # Post-process: Energy usage cannot be negative
        predictions = np.clip(predictions, a_min=0.0, a_max=None)
        return predictions

    def get_feature_importance(self, feature_names: list) -> pd.DataFrame:
        """
        Extracts and ranks feature importances based on Gain metric.

        Args:
            feature_names: List of column names corresponding to input features.

        Returns:
            pd.DataFrame: Sorted DataFrame of feature importances.
        """
        if self.model is None:
            error_msg = "Model is not trained. Cannot extract feature importance."
            logger.error(error_msg)
            raise ValueError(error_msg)

        importances = self.model.feature_importances_
        fi_df = pd.DataFrame(
            {"Feature": feature_names, "Importance": importances}
        ).sort_values(by="Importance", ascending=False).reset_index(drop=True)

        return fi_df

    def save(self, filepath: Path) -> None:
        """Saves serialized model instance to disk."""
        if self.model is None:
            logger.warning("Attempting to save an uninitialized model.")

        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "params": self.params}, filepath)
        logger.info(f"XGBoost model artifact saved to: {filepath}")

    @classmethod
    def load(cls, filepath: Path) -> "XGBoostForecaster":
        """Loads serialized model instance from disk."""
        if not filepath.exists():
            error_msg = f"Model artifact not found at: {filepath}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        data = joblib.load(filepath)
        forecaster = cls(hyperparams=data.get("params"))
        forecaster.model = data.get("model")
        logger.info(f"Loaded XGBoost model artifact from: {filepath}")
        return forecaster
