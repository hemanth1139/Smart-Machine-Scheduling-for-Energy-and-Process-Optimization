"""
Centralized Configuration Module for AI-Based Smart Machine Scheduling Project.
Provides non-hardcoded relative paths, constants, dataset schema specifications,
feature engineering hyper-parameters, forecasting settings, scheduling optimization,
and system directory management with strict path safety.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Tuple


class Config:
    """Project-wide configuration constants, directory paths, and hyperparameters."""

    # Base Directory (Project Root)
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    # Data Directories
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"

    # Dataset Input Paths
    ENERGY_DATA_FILENAME: str = "Steel_industry_data.csv"
    JOB_DATA_FILENAME: str = "job_table.csv"
    MACHINE_DATA_FILENAME: str = "machine_table.csv"

    @classmethod
    def get_raw_path(cls, filename: str) -> Path:
        """
        Returns raw dataset path with path traversal protection, checking data/raw first, then project root.

        Args:
            filename: Target file name string.

        Returns:
            Path: Resolved absolute pathlib Path object.
        """
        safe_filename = Path(filename).name

        raw_file = (cls.RAW_DATA_DIR / safe_filename).resolve()
        if raw_file.exists():
            return raw_file

        root_file = (cls.PROJECT_ROOT / safe_filename).resolve()
        if root_file.exists():
            return root_file

        return raw_file

    @classmethod
    def get_energy_data_path(cls) -> Path:
        """Returns resolved Path object for energy dataset."""
        return cls.get_raw_path(cls.ENERGY_DATA_FILENAME)

    @classmethod
    def get_job_data_path(cls) -> Path:
        """Returns resolved Path object for job dataset."""
        return cls.get_raw_path(cls.JOB_DATA_FILENAME)

    @classmethod
    def get_machine_data_path(cls) -> Path:
        """Returns resolved Path object for machine dataset."""
        return cls.get_raw_path(cls.MACHINE_DATA_FILENAME)

    # Output & Auxiliary Directories
    OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
    EDA_OUTPUT_DIR: Path = OUTPUTS_DIR / "eda"
    FORECAST_OUTPUT_DIR: Path = OUTPUTS_DIR / "forecasting"
    SCHEDULING_OUTPUT_DIR: Path = OUTPUTS_DIR / "scheduling"
    REPORTS_OUTPUT_DIR: Path = OUTPUTS_DIR / "reports"
    CHARTS_OUTPUT_DIR: Path = OUTPUTS_DIR / "charts"
    LOGS_OUTPUT_DIR: Path = PROJECT_ROOT / "logs"
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"

    # Global Constants
    RANDOM_SEED: int = 42

    # Energy Dataset Specific Settings
    ENERGY_TIME_COL: str = "date"
    ENERGY_TARGET_COL: str = "Usage_kWh"

    # Columns expecting normalized numeric types
    ENERGY_NUMERIC_COLS: List[str] = [
        "Usage_kWh",
        "Lagging_Current_Reactive.Power_kVarh",
        "Leading_Current_Reactive_Power_kVarh",
        "CO2(tCO2)",
        "Lagging_Current_Power_Factor",
        "Leading_Current_Power_Factor",
        "NSM",
    ]

    ENERGY_CATEGORICAL_COLS: List[str] = [
        "WeekStatus",
        "Day_of_week",
        "Load_Type",
    ]

    # Valid Numerical Ranges for Validation
    POWER_FACTOR_RANGE: Tuple[float, float] = (0.0, 100.0)
    NON_NEGATIVE_COLS: List[str] = [
        "Usage_kWh",
        "Lagging_Current_Reactive.Power_kVarh",
        "Leading_Current_Reactive_Power_kVarh",
        "CO2(tCO2)",
        "NSM",
    ]

    # Feature Engineering Hyperparameters
    LAG_STEPS: List[int] = [1, 2, 4, 96]
    ROLLING_WINDOWS: List[int] = [4, 96]

    # Output Processed Filenames
    ENERGY_CLEANED_FILENAME: str = "energy_cleaned.csv"
    ENERGY_ENGINEERED_FILENAME: str = "energy_engineered.csv"
    JOB_CLEANED_FILENAME: str = "jobs_cleaned.csv"
    MACHINE_CLEANED_FILENAME: str = "machines_cleaned.csv"

    # =========================================================================
    # FORECASTING CONFIGURATION
    # =========================================================================
    TRAIN_TEST_SPLIT_RATIO: float = 0.8
    MODEL_OUTPUT_PATH: Path = MODELS_DIR / "energy_xgb_model.joblib"
    PREPROCESSOR_OUTPUT_PATH: Path = MODELS_DIR / "preprocessor.joblib"
    PREDICTIONS_CSV_PATH: Path = FORECAST_OUTPUT_DIR / "predictions.csv"
    FUTURE_FORECAST_CSV_PATH: Path = FORECAST_OUTPUT_DIR / "future_forecast.csv"

    XGB_HYPERPARAMETERS: Dict[str, Any] = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "random_state": 42,
        "n_jobs": -1,
        "objective": "reg:squarederror",
    }
    FUTURE_FORECAST_STEPS: int = 96

    # =========================================================================
    # SCHEDULING OPTIMIZATION CONFIGURATION
    # =========================================================================
    SLOT_DURATION_MIN: int = 15
    SCHEDULING_HORIZON_SLOTS: int = 96
    ORTOOLS_TIME_LIMIT_SEC: float = 60.0

    TARIFF_PEAK_RATE: float = 0.25
    TARIFF_OFFPEAK_RATE: float = 0.10
    PEAK_HOURS_RANGE: Tuple[int, int] = (8, 20)

    WEIGHT_ENERGY_COST: float = 1.0
    WEIGHT_DEADLINE_PENALTY: float = 10.0
    WEIGHT_CHANGEOVER_PENALTY: float = 2.0
    WEIGHT_MAKESPAN: float = 0.5
    WEIGHT_IDLE_POWER: float = 0.2

    OPTIMIZED_SCHEDULE_FILENAME: str = "optimized_schedule.csv"
    FCFS_SCHEDULE_FILENAME: str = "fcfs_schedule.csv"
    KPI_SUMMARY_FILENAME: str = "kpi_summary.csv"
    COMPARISON_REPORT_FILENAME: str = "comparison_report.csv"

    @classmethod
    def create_directories(cls) -> None:
        """Ensure all required project directories exist with correct permissions."""
        directories = [
            cls.DATA_DIR,
            cls.RAW_DATA_DIR,
            cls.PROCESSED_DATA_DIR,
            cls.OUTPUTS_DIR,
            cls.EDA_OUTPUT_DIR,
            cls.FORECAST_OUTPUT_DIR,
            cls.SCHEDULING_OUTPUT_DIR,
            cls.REPORTS_OUTPUT_DIR,
            cls.CHARTS_OUTPUT_DIR,
            cls.LOGS_OUTPUT_DIR,
            cls.MODELS_DIR,
            cls.TEMP_DIR,
            cls.PROJECT_ROOT / "preprocessing",
            cls.PROJECT_ROOT / "forecasting",
            cls.PROJECT_ROOT / "scheduler",
            cls.PROJECT_ROOT / "dashboard",
            cls.PROJECT_ROOT / "utils",
            cls.PROJECT_ROOT / "tests",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Instantiate default config instance
config = Config()
