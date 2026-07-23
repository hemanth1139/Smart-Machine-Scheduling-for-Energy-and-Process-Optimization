"""
Abstract Base Model Class for Energy Demand Forecasting.
Defines a standard, extensible interface for regression models.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Union
import numpy as np
import pandas as pd


class BaseForecaster(ABC):
    """Abstract Base Class for modular forecasting models."""

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Union[pd.DataFrame, None] = None,
        y_val: Union[pd.Series, None] = None,
    ) -> "BaseForecaster":
        """
        Trains the forecasting regressor on historical training data.

        Args:
            X_train: Feature matrix for training.
            y_train: Target vector (Usage_kWh) for training.
            X_val: Optional validation feature matrix.
            y_val: Optional validation target vector.

        Returns:
            BaseForecaster: Self instance after training.
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generates energy demand predictions for feature matrix X.

        Args:
            X: Input feature matrix.

        Returns:
            np.ndarray: Predicted energy values (Usage_kWh).
        """
        pass

    @abstractmethod
    def get_feature_importance(self, feature_names: list) -> pd.DataFrame:
        """
        Extracts feature importances ranked in descending order.

        Args:
            feature_names: List of feature column names.

        Returns:
            pd.DataFrame: DataFrame containing Feature and Importance columns.
        """
        pass

    @abstractmethod
    def save(self, filepath: Path) -> None:
        """Serializes and saves model artifact to disk."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, filepath: Path) -> "BaseForecaster":
        """Loads serialized model artifact from disk."""
        pass
