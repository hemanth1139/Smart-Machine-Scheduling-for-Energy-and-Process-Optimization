"""
Feature Engineering Module for Time-Series Energy Forecasting.
Generates reusable temporal, cyclical, lag, and rolling statistics features.
Designed for both batch dataset preparation and real-time/streaming inference.
"""

from typing import List, Optional
import numpy as np
import pandas as pd

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """Reusable feature engineering transformer for time-series energy consumption data."""

    def __init__(
        self,
        target_col: str = Config.ENERGY_TARGET_COL,
        time_col: str = Config.ENERGY_TIME_COL,
        lag_steps: Optional[List[int]] = None,
        rolling_windows: Optional[List[int]] = None,
    ):
        self.target_col = target_col
        self.time_col = time_col
        self.lag_steps = lag_steps if lag_steps is not None else Config.LAG_STEPS
        self.rolling_windows = (
            rolling_windows if rolling_windows is not None else Config.ROLLING_WINDOWS
        )

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts temporal and cyclical datetime features from the timestamp column.

        Generated Features:
            - hour: Hour of day [0..23]
            - day: Day of month [1..31]
            - month: Month [1..12]
            - day_of_week: Day of week index [0..6] (Monday=0)
            - quarter: Year quarter [1..4]
            - day_of_year: Day of year [1..366]
            - is_weekend: Binary indicator (1 if Saturday/Sunday else 0)
            - nsm: Number of seconds from midnight
            - hour_sin / hour_cos: Cyclical sin/cos encodings for hour of day
            - month_sin / month_cos: Cyclical sin/cos encodings for month of year

        Args:
            df: Input DataFrame containing datetime column.

        Returns:
            pd.DataFrame: DataFrame augmented with temporal features.
        """
        df_feat = df.copy()

        if self.time_col not in df_feat.columns:
            logger.warning(f"Time column '{self.time_col}' not found. Skipping time features.")
            return df_feat

        # Ensure datetime dtype
        dt_s = pd.to_datetime(df_feat[self.time_col])

        logger.info(f"Extracting temporal and cyclical features from '{self.time_col}'...")

        df_feat["hour"] = dt_s.dt.hour
        df_feat["day"] = dt_s.dt.day
        df_feat["month"] = dt_s.dt.month
        df_feat["day_of_week"] = dt_s.dt.dayofweek
        df_feat["quarter"] = dt_s.dt.quarter
        df_feat["day_of_year"] = dt_s.dt.dayofyear
        df_feat["is_weekend"] = dt_s.dt.dayofweek.isin([5, 6]).astype(int)

        # Seconds from midnight (NSM) if not already present or refresh it
        df_feat["nsm_computed"] = (
            dt_s.dt.hour * 3600 + dt_s.dt.minute * 60 + dt_s.dt.second
        )

        # Cyclical Encodings (Harmonic Representations)
        df_feat["hour_sin"] = np.sin(2 * np.pi * df_feat["hour"] / 24.0)
        df_feat["hour_cos"] = np.cos(2 * np.pi * df_feat["hour"] / 24.0)
        df_feat["month_sin"] = np.sin(2 * np.pi * (df_feat["month"] - 1) / 12.0)
        df_feat["month_cos"] = np.cos(2 * np.pi * (df_feat["month"] - 1) / 12.0)

        logger.info("Temporal and cyclical feature extraction completed.")
        return df_feat

    def add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates historical lag features for the target energy usage variable.

        Args:
            df: Input DataFrame sorted chronologically.

        Returns:
            pd.DataFrame: DataFrame augmented with lag features.
        """
        df_feat = df.copy()

        if self.target_col not in df_feat.columns:
            logger.warning(f"Target column '{self.target_col}' not found. Skipping lag features.")
            return df_feat

        logger.info(f"Generating lag features for '{self.target_col}' using steps: {self.lag_steps}...")

        for lag in self.lag_steps:
            col_name = f"{self.target_col}_lag_{lag}"
            df_feat[col_name] = df_feat[self.target_col].shift(lag)

        # 1-step lag difference / energy usage acceleration
        df_feat[f"{self.target_col}_diff_1"] = df_feat[self.target_col].diff(1)

        logger.info("Lag features generated successfully.")
        return df_feat

    def add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates rolling window statistical features (Mean, Std, Min, Max).

        Args:
            df: Input DataFrame sorted chronologically.

        Returns:
            pd.DataFrame: DataFrame augmented with rolling window statistics.
        """
        df_feat = df.copy()

        if self.target_col not in df_feat.columns:
            logger.warning(f"Target column '{self.target_col}' not found. Skipping rolling features.")
            return df_feat

        logger.info(
            f"Generating rolling window features for '{self.target_col}' "
            f"with windows: {self.rolling_windows}..."
        )

        for w in self.rolling_windows:
            # Shift 1 to prevent data leakage (use historical steps up to t-1 for window)
            shifted_s = df_feat[self.target_col].shift(1)
            
            df_feat[f"{self.target_col}_rolling_mean_{w}"] = (
                shifted_s.rolling(window=w, min_periods=1).mean()
            )
            df_feat[f"{self.target_col}_rolling_std_{w}"] = (
                shifted_s.rolling(window=w, min_periods=1).std().fillna(0)
            )
            df_feat[f"{self.target_col}_rolling_min_{w}"] = (
                shifted_s.rolling(window=w, min_periods=1).min()
            )
            df_feat[f"{self.target_col}_rolling_max_{w}"] = (
                shifted_s.rolling(window=w, min_periods=1).max()
            )

        # Exponential Weighted Moving Average (EWMA)
        df_feat[f"{self.target_col}_ewma_4"] = (
            df_feat[self.target_col].shift(1).ewm(span=4, adjust=False).mean()
        )

        logger.info("Rolling window features generated successfully.")
        return df_feat

    def transform(self, df: pd.DataFrame, fill_na: bool = True) -> pd.DataFrame:
        """
        Executes complete feature engineering pipeline on energy dataframe.

        Args:
            df: Cleaned energy DataFrame.
            fill_na: If True, backfills initial NA values caused by lagging/rolling.

        Returns:
            pd.DataFrame: Complete feature-engineered DataFrame.
        """
        logger.info("Starting complete Feature Engineering transformation pipeline...")
        df_feat = self.add_time_features(df)
        df_feat = self.add_lag_features(df_feat)
        df_feat = self.add_rolling_features(df_feat)

        if fill_na:
            initial_nas = df_feat.isnull().sum().sum()
            # Backfill initial NA rows resulting from lag shifting
            df_feat = df_feat.bfill().ffill()
            final_nas = df_feat.isnull().sum().sum()
            logger.info(f"Filled initial lag/rolling NA values (Initial NAs: {initial_nas}, Final NAs: {final_nas}).")

        logger.info(
            f"Feature engineering transformation completed successfully. "
            f"New Dataset Shape: {df_feat.shape}"
        )
        return df_feat
