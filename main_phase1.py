"""
Main Entry Point for Phase 1: Data Preparation & Preprocessing.
Orchestrates raw dataset loading, validation, cleaning, feature engineering,
and exports processed feature-engineered CSVs to outputs/data/processed/.
"""

import sys
from pathlib import Path

# Add project root directory to python module search path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config, config
from utils.logger import setup_logger
from preprocessing.loader import DataLoader
from preprocessing.validator import DataValidator
from preprocessing.cleaner import DataCleaner
from preprocessing.feature_engineering import FeatureEngineer

# Initialize logger instance for Phase 1
logger = setup_logger("SmartSchedulingPhase1", log_file=Config.LOGS_OUTPUT_DIR / "preprocessing.log")


def run_phase_1_pipeline() -> None:
    """Executes complete Phase 1 Data Preparation & Feature Engineering pipeline."""
    logger.info("======================================================================")
    logger.info("Starting Phase 1 Execution: Data Loading, Validation & Feature Engineering")
    logger.info("======================================================================")

    # Step 1: Ensure required output directories exist
    Config.create_directories()

    # Step 2: Load raw datasets
    logger.info("Step 1/5: Loading raw datasets (Energy, Job, Machine)...")
    loader = DataLoader(cfg=config)
    energy_df, job_df, machine_df = loader.load_all()

    # Step 3: Validate datasets and generate data quality report
    logger.info("Step 2/5: Running automated data quality validation checks...")
    validator = DataValidator(cfg=config)
    validation_results = validator.validate_all_and_save_report(
        energy_df=energy_df,
        job_df=job_df,
        machine_df=machine_df,
        save_path=Config.REPORTS_OUTPUT_DIR / "data_validation_report.md",
    )

    # Log top-level validation summary
    for ds_name, result in validation_results.items():
        logger.info(
            f"  [{ds_name}] Rows: {result['dimensions']['rows']}, "
            f"Duplicates: {result['duplicate_rows']}, "
            f"Missing: {result['total_missing_cells']}, "
            f"Invalid Warnings: {len(result['invalid_value_warnings'])}"
        )

    # Step 4: Clean datasets
    logger.info("Step 3/5: Executing data cleaning pipeline (deduplication, type conversion, imputation)...")
    cleaner = DataCleaner(cfg=config)
    energy_clean = cleaner.clean_energy_data(energy_df)
    job_clean = cleaner.clean_job_data(job_df)
    machine_clean = cleaner.clean_machine_data(machine_df)

    # Save cleaned job and machine datasets
    job_clean_path = Config.PROCESSED_DATA_DIR / Config.JOB_CLEANED_FILENAME
    machine_clean_path = Config.PROCESSED_DATA_DIR / Config.MACHINE_CLEANED_FILENAME
    job_clean.to_csv(job_clean_path, index=False)
    machine_clean.to_csv(machine_clean_path, index=False)
    logger.info(f"Cleaned job dataset saved to: {job_clean_path}")
    logger.info(f"Cleaned machine dataset saved to: {machine_clean_path}")

    # Step 5: Feature Engineering on Energy Dataset
    logger.info("Step 4/5: Applying feature engineering (lag features, rolling stats, cyclical encodings)...")
    feature_engineer = FeatureEngineer(
        target_col=Config.ENERGY_TARGET_COL,
        time_col=Config.ENERGY_TIME_COL,
        lag_steps=Config.LAG_STEPS,
        rolling_windows=Config.ROLLING_WINDOWS,
    )
    energy_engineered = feature_engineer.transform(energy_clean, fill_na=True)

    # Step 6: Save feature-engineered energy dataset
    logger.info("Step 5/5: Exporting feature-engineered energy dataset...")
    engineered_path = Config.PROCESSED_DATA_DIR / Config.ENERGY_ENGINEERED_FILENAME
    energy_engineered.to_csv(engineered_path, index=False)
    logger.info(f"Feature-engineered energy dataset saved to: {engineered_path} | Shape: {energy_engineered.shape}")

    logger.info("======================================================================")
    logger.info("PHASE 1 EXECUTION COMPLETE SUCCESSFULLY!")
    logger.info(f"Processed Data Directory: {Config.PROCESSED_DATA_DIR}")
    logger.info(f"  • Energy (engineered): {Config.ENERGY_ENGINEERED_FILENAME}")
    logger.info(f"  • Jobs (cleaned):      {Config.JOB_CLEANED_FILENAME}")
    logger.info(f"  • Machines (cleaned):  {Config.MACHINE_CLEANED_FILENAME}")
    logger.info("Ready for Phase 2: XGBoost Energy Demand Forecasting.")
    logger.info("======================================================================")


if __name__ == "__main__":
    run_phase_1_pipeline()
