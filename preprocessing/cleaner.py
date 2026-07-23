"""
Data Cleaning & Standardization Preprocessing Module.
Provides reusable, modular cleaning functions for missing value handling,
duplicate removal, type conversions, and column name normalization.
"""

from typing import Optional, List, Dict, Union
import re
import pandas as pd
import numpy as np

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes dataframe column names to clean, consistent format.
    Preserves readable capitalization where standard, or converts special chars to clean underscores.

    Args:
        df: Input pandas DataFrame.

    Returns:
        pd.DataFrame: DataFrame with normalized column names.
    """
    df_clean = df.copy()
    cleaned_cols = []
    for col in df_clean.columns:
        # Replace brackets, parentheses, dots, spaces with underscores
        c = re.sub(r"[ ()\.\-\/]", "_", col.strip())
        # Replace multiple underscores with single underscore
        c = re.sub(r"__+", "_", c)
        c = c.strip("_")
        cleaned_cols.append(c)
    
    df_clean.columns = cleaned_cols
    logger.debug(f"Normalized column names: {cleaned_cols}")
    return df_clean


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Identifies and removes duplicate rows from dataframe.

    Args:
        df: Input pandas DataFrame.
        subset: Optional list of columns to consider for identifying duplicates.

    Returns:
        pd.DataFrame: Deduplicated DataFrame.
    """
    initial_count = len(df)
    df_clean = df.drop_duplicates(subset=subset).reset_index(drop=True)
    removed_count = initial_count - len(df_clean)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate rows (from {initial_count} to {len(df_clean)}).")
    else:
        logger.info("No duplicate rows detected.")
    return df_clean


def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = "forward_fill",
    numeric_fill: Optional[Union[float, int]] = None,
    categorical_fill: str = "Unknown",
) -> pd.DataFrame:
    """
    Handles missing values using configurable domain strategies.

    Args:
        df: Input pandas DataFrame.
        strategy: 'forward_fill', 'interpolate', 'drop', or 'constant'.
        numeric_fill: Constant value to fill numeric NAs if strategy='constant'.
        categorical_fill: Constant string to fill categorical NAs.

    Returns:
        pd.DataFrame: DataFrame with handled missing values.
    """
    df_clean = df.copy()
    total_na = df_clean.isnull().sum().sum()
    if total_na == 0:
        logger.info("No missing values found to handle.")
        return df_clean

    logger.info(f"Handling {total_na} missing values using strategy: '{strategy}'")

    if strategy == "forward_fill":
        df_clean = df_clean.ffill().bfill()
    elif strategy == "interpolate":
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method="linear").ffill().bfill()
        non_numeric = [c for c in df_clean.columns if c not in numeric_cols]
        if non_numeric:
            df_clean[non_numeric] = df_clean[non_numeric].fillna(categorical_fill)
    elif strategy == "drop":
        df_clean = df_clean.dropna().reset_index(drop=True)
    elif strategy == "constant":
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        if numeric_fill is not None:
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(numeric_fill)
        cat_cols = df_clean.select_dtypes(exclude=[np.number]).columns
        df_clean[cat_cols] = df_clean[cat_cols].fillna(categorical_fill)

    remaining_na = df_clean.isnull().sum().sum()
    logger.info(f"Missing value handling complete. Remaining NAs: {remaining_na}")
    return df_clean


def convert_data_types(
    df: pd.DataFrame,
    datetime_cols: Optional[List[str]] = None,
    numeric_cols: Optional[List[str]] = None,
    categorical_cols: Optional[List[str]] = None,
    datetime_format: Optional[str] = None,
) -> pd.DataFrame:
    """
    Converts dataframe columns to proper data types (datetime, numeric, categorical).

    Args:
        df: Input pandas DataFrame.
        datetime_cols: List of column names to parse as datetime.
        numeric_cols: List of column names to cast to float/int.
        categorical_cols: List of column names to cast to category/str.
        datetime_format: Optional explicit datetime parsing format string.

    Returns:
        pd.DataFrame: Type-converted DataFrame.
    """
    df_clean = df.copy()

    if datetime_cols:
        for col in datetime_cols:
            if col in df_clean.columns:
                try:
                    if datetime_format:
                        df_clean[col] = pd.to_datetime(df_clean[col], format=datetime_format, errors="coerce")
                    else:
                        # Attempt standard parsing with dayfirst heuristic for DD/MM/YYYY
                        df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce", dayfirst=True)
                    logger.info(f"Converted '{col}' to datetime. Sample: {df_clean[col].iloc[0]}")
                except Exception as e:
                    logger.error(f"Error converting column '{col}' to datetime: {e}")

    if numeric_cols:
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    if categorical_cols:
        for col in categorical_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype("category")

    return df_clean


class DataCleaner:
    """Class orchestrating domain-specific dataset cleaning pipelines."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def clean_energy_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes end-to-end cleaning on the Steel Industry Energy Dataset.

        Args:
            df: Raw energy consumption DataFrame.

        Returns:
            pd.DataFrame: Cleaned energy DataFrame.
        """
        logger.info("Starting cleaning pipeline for Energy Dataset...")
        df_clean = remove_duplicates(df)
        df_clean = convert_data_types(
            df_clean,
            datetime_cols=[self.cfg.ENERGY_TIME_COL],
            numeric_cols=self.cfg.ENERGY_NUMERIC_COLS,
            categorical_cols=self.cfg.ENERGY_CATEGORICAL_COLS,
        )
        df_clean = handle_missing_values(df_clean, strategy="forward_fill")

        # Ensure date column is sorted sequentially
        if self.cfg.ENERGY_TIME_COL in df_clean.columns and pd.api.types.is_datetime64_any_dtype(df_clean[self.cfg.ENERGY_TIME_COL]):
            df_clean = df_clean.sort_values(by=self.cfg.ENERGY_TIME_COL).reset_index(drop=True)

        logger.info("Energy Dataset cleaning pipeline complete.")
        return df_clean

    def clean_job_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes cleaning pipeline on the Synthetic Job Dataset.

        Args:
            df: Raw job DataFrame.

        Returns:
            pd.DataFrame: Cleaned job DataFrame.
        """
        logger.info("Starting cleaning pipeline for Job Dataset...")
        df_clean = remove_duplicates(df, subset=["Job_ID"] if "Job_ID" in df.columns else None)
        df_clean = convert_data_types(
            df_clean,
            datetime_cols=["Deadline", "Arrival_Time"],
            numeric_cols=["Duration_min"],
            categorical_cols=["Priority"],
        )
        df_clean = handle_missing_values(df_clean, strategy="constant", categorical_fill="Medium")
        logger.info("Job Dataset cleaning pipeline complete.")
        return df_clean

    def clean_machine_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes cleaning pipeline on the Synthetic Machine Dataset.

        Args:
            df: Raw machine DataFrame.

        Returns:
            pd.DataFrame: Cleaned machine DataFrame.
        """
        logger.info("Starting cleaning pipeline for Machine Dataset...")
        df_clean = remove_duplicates(df, subset=["Machine_ID"] if "Machine_ID" in df.columns else None)
        df_clean = convert_data_types(
            df_clean,
            numeric_cols=["Idle_Power_kW", "Active_Power_kW", "Changeover_Time_min"],
            categorical_cols=["Machine_Type"],
        )
        df_clean = handle_missing_values(df_clean, strategy="constant")
        logger.info("Machine Dataset cleaning pipeline complete.")
        return df_clean
