"""
Automated Test for Preprocessing, Validation, Cleaning & Feature Engineering.
"""

import pandas as pd
import numpy as np

from preprocessing.cleaner import remove_duplicates, handle_missing_values, normalize_column_names
from preprocessing.feature_engineering import FeatureEngineer
from preprocessing.validator import DataValidator


def test_cleaner_functions():
    """Tests deduplication, column normalization, and NA handling."""
    df_raw = pd.DataFrame({
        "  Usage (kWh) ": [3.0, 3.0, None, 5.0],
        "Load Type": ["Light", "Light", "Medium", "High"],
    })

    df_norm = normalize_column_names(df_raw)
    assert "Usage_kWh" in df_norm.columns or "Usage_kWh" in df_norm.columns

    df_dedup = remove_duplicates(df_norm)
    assert len(df_dedup) == 3

    df_clean = handle_missing_values(df_dedup, strategy="forward_fill")
    assert df_clean.isnull().sum().sum() == 0


def test_feature_engineering():
    """Tests temporal, lag, and rolling feature generation."""
    dates = pd.date_range(start="2026-01-01", periods=100, freq="15min")
    df = pd.DataFrame({"date": dates, "Usage_kWh": np.random.uniform(2.0, 10.0, 100)})

    fe = FeatureEngineer(target_col="Usage_kWh", time_col="date", lag_steps=[1, 2], rolling_windows=[4])
    df_feat = fe.transform(df)

    assert "hour" in df_feat.columns
    assert "is_weekend" in df_feat.columns
    assert "Usage_kWh_lag_1" in df_feat.columns
    assert "Usage_kWh_rolling_mean_4" in df_feat.columns
    assert df_feat.isnull().sum().sum() == 0
