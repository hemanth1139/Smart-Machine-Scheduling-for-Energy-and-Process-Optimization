"""
Centralized Configuration Module for the Predict-then-Optimize Scheduling Framework.
"""

from pathlib import Path
from typing import Dict, List, Any, Tuple


class Config:
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
        safe_filename = Path(filename).name
        raw_file = (cls.RAW_DATA_DIR / safe_filename).resolve()
        if raw_file.exists():
            return raw_file
        return (cls.PROJECT_ROOT / safe_filename).resolve()

    @classmethod
    def get_energy_data_path(cls) -> Path:
        return cls.get_raw_path(cls.ENERGY_DATA_FILENAME)

    @classmethod
    def get_job_data_path(cls) -> Path:
        return cls.get_raw_path(cls.JOB_DATA_FILENAME)

    @classmethod
    def get_machine_data_path(cls) -> Path:
        return cls.get_raw_path(cls.MACHINE_DATA_FILENAME)

    # Output & Model Directories
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    MODELS_DIR: Path = PROJECT_ROOT / "backend" / "models"

    # Global Constants
    RANDOM_SEED: int = 42

    # Target and Numerical Columns
    ENERGY_TIME_COL: str = "date"
    ENERGY_TARGET_COL: str = "Usage_kWh"

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

    # Feature Engineering Parameters
    LAG_STEPS: List[int] = [1, 2, 4, 96]
    ROLLING_WINDOWS: List[int] = [4, 96]

    # XGBoost Regressor Hyperparameters
    XGB_HYPERPARAMETERS: Dict[str, Any] = {
        "n_estimators": 300,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1,
    }
    
    # Scheduling Parameters
    SLOT_DURATION_MIN: int = 15
    SCHEDULING_HORIZON_SLOTS: int = 192  # 48 hours (192 intervals of 15 min)
    ORTOOLS_TIME_LIMIT_SEC: float = 120.0

    # Tariffs per Load Type (INR per kWh)
    TARIFF_MAX_LOAD: float = 12.0
    TARIFF_MED_LOAD: float = 7.5
    TARIFF_LIGHT_LOAD: float = 4.0

    # Grid constraints — soft peak target used by FD-PDTS peak guard.
    # Sized below typical FCFS simultaneous draw so energy-aware methods reduce peaks.
    PEAK_GRID_CAPACITY_KW: float = 420.0

    # Optimization Weights (scaled for integer optimization)
    # Energy is the primary publication objective; light tardiness regularizer in hybrid
    WEIGHT_ENERGY_COST: int = 20
    WEIGHT_MAKESPAN: int = 5
    WEIGHT_EMISSIONS: int = 8
    WEIGHT_POWER_FACTOR_PENALTY: int = 12

    # Output Filenames
    OPTIMIZED_SCHEDULE_FILENAME: str = "optimized_schedule.csv"
    COMPARISON_REPORT_FILENAME: str = "comparison_report.csv"

    @classmethod
    def create_directories(cls) -> None:
        """Create all folders."""
        for path in [cls.DATA_DIR, cls.RAW_DATA_DIR, cls.PROCESSED_DATA_DIR, cls.OUTPUT_DIR, cls.MODELS_DIR]:
            path.mkdir(parents=True, exist_ok=True)


config = Config()
