"""
Data Preparation & Time-Series Aware Splitting Module.
Prepares features, handles categorical encoding, scaling, and strictly chronological train/test splitting.
"""

from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
import joblib

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class DataPreparer:
    """Handles dataset loading, categorical encoding, feature scaling, and time-series train/test splitting."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg
        self.encoder: Optional[OrdinalEncoder] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_columns: List[str] = []

    def prepare_data(
        self, df: pd.DataFrame, train_ratio: Optional[float] = None
    ) -> Tuple[
        pd.DataFrame,
        pd.Series,
        pd.DataFrame,
        pd.Series,
        pd.Series,
        pd.Series,
    ]:
        """
        Processes feature matrix and executes time-series (chronological) train/test split.

        Args:
            df: Feature-engineered pandas DataFrame.
            train_ratio: Fraction of dataset reserved for training (e.g. 0.8).

        Returns:
            Tuple containing:
            - X_train: Training feature DataFrame
            - y_train: Training target Series (Usage_kWh)
            - X_test: Testing feature DataFrame
            - y_test: Testing target Series (Usage_kWh)
            - dates_train: Datetime index/series for training set
            - dates_test: Datetime index/series for testing set
        """
        if train_ratio is None:
            train_ratio = self.cfg.TRAIN_TEST_SPLIT_RATIO

        logger.info(f"Starting data preparation. Input dataset shape: {df.shape}")

        df_proc = df.copy()

        # Ensure date column is preserved for time tracking
        time_col = self.cfg.ENERGY_TIME_COL
        target_col = self.cfg.ENERGY_TARGET_COL

        if time_col not in df_proc.columns:
            raise KeyError(f"Timestamp column '{time_col}' missing from input dataset.")
        if target_col not in df_proc.columns:
            raise KeyError(f"Target column '{target_col}' missing from input dataset.")

        # Ensure chronological ordering
        df_proc[time_col] = pd.to_datetime(df_proc[time_col])
        df_proc = df_proc.sort_values(by=time_col).reset_index(drop=True)

        dates = df_proc[time_col]
        y = df_proc[target_col]

        # Select Feature Columns (exclude raw date, target, and redundant unencoded text)
        exclude_cols = [time_col, target_col, "nsm_computed"]
        feature_cols = [c for c in df_proc.columns if c not in exclude_cols]

        X = df_proc[feature_cols].copy()

        # Handle Categorical Features (Ordinal Encoding)
        # This includes the tariff-proxy and time-status features specified in the project requirements:
        #   - Load_Type  (Light_Load / Medium_Load / Maximum_Load — maps to tariff period)
        #   - WeekStatus (Weekday / Weekend)
        #   - Day_of_week (Sunday ... Saturday)
        cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

        # Explicitly ensure required spec features are captured even if dtype changed
        spec_cat_features = ["Load_Type", "WeekStatus", "Day_of_week"]
        for col in spec_cat_features:
            if col in X.columns and col not in cat_cols:
                X[col] = X[col].astype("category")
                cat_cols.append(col)
                logger.info(f"Forced categorical dtype for spec-required feature: '{col}'")

        if cat_cols:
            logger.info(
                f"Encoding categorical features via OrdinalEncoder: {cat_cols}\n"
                f"  → Confirmed tariff-proxy features present: "
                f"{[c for c in spec_cat_features if c in cat_cols]}"
            )
            self.encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
            X[cat_cols] = self.encoder.fit_transform(X[cat_cols])
        else:
            logger.warning(
                "No categorical columns detected. Verify that Load_Type, WeekStatus, "
                "and Day_of_week columns are present in the raw dataset."
            )

        self.feature_columns = X.columns.tolist()

        # Time-Series Aware Chronological Split (Do NOT shuffle!)
        split_idx = int(len(X) * train_ratio)

        X_train = X.iloc[:split_idx].copy()
        y_train = y.iloc[:split_idx].copy()
        dates_train = dates.iloc[:split_idx].copy()

        X_test = X.iloc[split_idx:].copy()
        y_test = y.iloc[split_idx:].copy()
        dates_test = dates.iloc[split_idx:].copy()

        logger.info(
            f"Time-series chronological split complete ({train_ratio*100:.0f}% Train / {(1-train_ratio)*100:.0f}% Test): "
            f"Train Shape: {X_train.shape}, Test Shape: {X_test.shape}"
        )
        logger.info(
            f"Train Period: {dates_train.iloc[0]} to {dates_train.iloc[-1]} | "
            f"Test Period: {dates_test.iloc[0]} to {dates_test.iloc[-1]}"
        )

        return X_train, y_train, X_test, y_test, dates_train, dates_test

    def save_preprocessor(self, filepath: Path) -> None:
        """Saves encoder/scaler preprocessor state to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "encoder": self.encoder,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
        }
        joblib.dump(state, filepath)
        logger.info(f"Preprocessor artifact saved to: {filepath}")

    @classmethod
    def load_preprocessor(cls, filepath: Path) -> "DataPreparer":
        """Loads encoder/scaler preprocessor state from disk."""
        if not filepath.exists():
            raise FileNotFoundError(f"Preprocessor artifact not found at: {filepath}")

        state = joblib.load(filepath)
        preparer = cls()
        preparer.encoder = state.get("encoder")
        preparer.scaler = state.get("scaler")
        preparer.feature_columns = state.get("feature_columns", [])
        logger.info(f"Loaded preprocessor artifact from: {filepath}")
        return preparer
