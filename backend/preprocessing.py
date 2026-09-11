"""
Data Loading, Cleaning, and Feature Engineering preprocessing module.

Fix (v2): Lagging_Current_Power_Factor is recorded in the raw SCADA dataset on a
0-100 percentage scale. Training directly on this scale causes its large gradient
magnitude to dominate the shared custom quantile objective and collapse energy
predictions. We therefore scale PF to decimal [0.0, 1.0] before constructing
the target matrix, and record the scale factor so predictions can be
inverse-transformed.
"""

from pathlib import Path
from typing import Tuple, List, Optional
import re
import pandas as pd
import numpy as np
from sklearn.preprocessing import OrdinalEncoder
import joblib

try:
    from backend.config import config
except ImportError:
    from config import config

# Scale factor: raw PF is in percent (0-100); we train on decimal (0-1)
PF_SCALE = 100.0


class DataLoader:
    @staticmethod
    def load_energy_data() -> pd.DataFrame:
        path = config.get_energy_data_path()
        if not path.exists():
            raise FileNotFoundError(f"Energy dataset not found at {path}")
        return pd.read_csv(path)

    @staticmethod
    def load_job_data() -> pd.DataFrame:
        path = config.get_job_data_path()
        if not path.exists():
            raise FileNotFoundError(f"Job dataset not found at {path}")
        return pd.read_csv(path)

    @staticmethod
    def load_machine_data() -> pd.DataFrame:
        path = config.get_machine_data_path()
        if not path.exists():
            raise FileNotFoundError(f"Machine dataset not found at {path}")
        return pd.read_csv(path)


class DataCleaner:
    @staticmethod
    def clean_energy_data(df: pd.DataFrame) -> pd.DataFrame:
        df_clean = df.drop_duplicates().copy()

        # DateTime conversion
        df_clean[config.ENERGY_TIME_COL] = pd.to_datetime(
            df_clean[config.ENERGY_TIME_COL], errors="coerce", dayfirst=True
        )

        # Numeric conversions
        for col in config.ENERGY_NUMERIC_COLS:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

        # Categorical conversions
        for col in config.ENERGY_CATEGORICAL_COLS:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype("category")

        # Fill missing values
        df_clean = df_clean.ffill().bfill()
        return df_clean.sort_values(by=config.ENERGY_TIME_COL).reset_index(drop=True)

    @staticmethod
    def clean_job_data(df: pd.DataFrame) -> pd.DataFrame:
        df_clean = df.drop_duplicates(subset=["Job_ID"]).copy()
        df_clean["Duration_min"] = pd.to_numeric(df_clean["Duration_min"], errors="coerce")
        df_clean["Deadline"] = pd.to_numeric(df_clean["Deadline"], errors="coerce")
        df_clean["Priority"] = pd.to_numeric(df_clean["Priority"], errors="coerce")
        df_clean = df_clean.ffill().bfill()
        return df_clean

    @staticmethod
    def clean_machine_data(df: pd.DataFrame) -> pd.DataFrame:
        df_clean = df.drop_duplicates(subset=["Machine_ID"]).copy()
        df_clean["Idle_Power_kW"] = pd.to_numeric(df_clean["Idle_Power_kW"], errors="coerce")
        df_clean["Active_Power_kW"] = pd.to_numeric(df_clean["Active_Power_kW"], errors="coerce")
        df_clean["Setup_Energy_kW"] = pd.to_numeric(df_clean["Setup_Energy_kW"], errors="coerce")
        return df_clean


class FeatureEngineer:
    def __init__(self):
        self.target_col = config.ENERGY_TARGET_COL
        self.time_col = config.ENERGY_TIME_COL
        self.lag_steps = config.LAG_STEPS
        self.rolling_windows = config.ROLLING_WINDOWS

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df_feat = df.copy()
        dt_s = pd.to_datetime(df_feat[self.time_col])

        # Temporal Features
        df_feat["hour"] = dt_s.dt.hour
        df_feat["day"] = dt_s.dt.day
        df_feat["month"] = dt_s.dt.month
        df_feat["day_of_week"] = dt_s.dt.dayofweek
        df_feat["is_weekend"] = dt_s.dt.dayofweek.isin([5, 6]).astype(int)

        # Cyclical Encodings
        df_feat["hour_sin"] = np.sin(2 * np.pi * df_feat["hour"] / 24.0)
        df_feat["hour_cos"] = np.cos(2 * np.pi * df_feat["hour"] / 24.0)
        df_feat["month_sin"] = np.sin(2 * np.pi * (df_feat["month"] - 1) / 12.0)
        df_feat["month_cos"] = np.cos(2 * np.pi * (df_feat["month"] - 1) / 12.0)

        # Lag Features for active power (all shifted — no leakage)
        for lag in self.lag_steps:
            df_feat[f"{self.target_col}_lag_{lag}"] = df_feat[self.target_col].shift(lag)
        df_feat[f"{self.target_col}_diff_1"] = df_feat[self.target_col].diff(1)

        # Rolling Window Features (all shifted by 1 to prevent data leakage)
        for w in self.rolling_windows:
            shifted_s = df_feat[self.target_col].shift(1)
            df_feat[f"{self.target_col}_rolling_mean_{w}"] = shifted_s.rolling(window=w, min_periods=1).mean()
            df_feat[f"{self.target_col}_rolling_std_{w}"] = (
                shifted_s.rolling(window=w, min_periods=1).std().fillna(0)
            )
            df_feat[f"{self.target_col}_rolling_min_{w}"] = shifted_s.rolling(window=w, min_periods=1).min()
            df_feat[f"{self.target_col}_rolling_max_{w}"] = shifted_s.rolling(window=w, min_periods=1).max()

        df_feat[f"{self.target_col}_ewma_4"] = (
            df_feat[self.target_col].shift(1).ewm(span=4, adjust=False).mean()
        )

        # Fill any NaNs created by shifts
        df_feat = df_feat.bfill().ffill()
        return df_feat


class DataPreparer:
    """
    Prepares train/test splits.

    Power factor fix: raw Lagging_Current_Power_Factor is in percent [0, 100].
    We divide by PF_SCALE=100 before training so all three target columns
    (Usage_kWh, CO2, PF_decimal) have roughly similar magnitudes, preventing
    the PF gradient from collapsing energy predictions.
    The inverse transform (x PF_SCALE) is applied in ForecastingPredictor.
    """

    PF_SCALE: float = PF_SCALE  # 100.0
    PF_COL: str = "Lagging_Current_Power_Factor"

    def __init__(self):
        self.encoder = None

    def prepare_data(
        self, df: pd.DataFrame, train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        df_proc = df.copy()

        # Ensure chronological order — critical for time-series split
        df_proc[config.ENERGY_TIME_COL] = pd.to_datetime(df_proc[config.ENERGY_TIME_COL])
        df_proc = df_proc.sort_values(by=config.ENERGY_TIME_COL).reset_index(drop=True)

        dates = df_proc[config.ENERGY_TIME_COL]

        # Targets
        y_cols = ["Usage_kWh", "CO2(tCO2)", self.PF_COL]
        y = df_proc[y_cols].copy()

        # KEY FIX: scale PF from percentage to decimal [0,1] before training
        y[self.PF_COL] = y[self.PF_COL] / self.PF_SCALE

        # Feature matrix (exclude time and raw targets)
        exclude_cols = [config.ENERGY_TIME_COL] + y_cols
        feature_cols = [c for c in df_proc.columns if c not in exclude_cols]
        X = df_proc[feature_cols].copy()

        # Encode categorical columns
        cat_cols = ["Load_Type", "WeekStatus", "Day_of_week"]
        for col in cat_cols:
            if col in X.columns:
                X[col] = X[col].astype("category")

        self.encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X[cat_cols] = self.encoder.fit_transform(X[cat_cols])

        # Train/Test chronological split — no shuffling
        split_idx = int(len(X) * train_ratio)

        X_train = X.iloc[:split_idx].copy()
        y_train = y.iloc[:split_idx].copy()
        dates_train = dates.iloc[:split_idx].copy()

        X_test = X.iloc[split_idx:].copy()
        y_test = y.iloc[split_idx:].copy()
        dates_test = dates.iloc[split_idx:].copy()

        return X_train, y_train, X_test, y_test, dates_train, dates_test

    def save_preprocessor(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"encoder": self.encoder, "pf_scale": self.PF_SCALE}, path)

    @classmethod
    def load_preprocessor(cls, path: Path) -> "DataPreparer":
        data = joblib.load(path)
        prep = cls()
        prep.encoder = data["encoder"]
        return prep
