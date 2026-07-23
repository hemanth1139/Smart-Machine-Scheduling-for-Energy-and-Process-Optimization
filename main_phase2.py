"""
Main Entry Point for Phase 2: AI-Based Smart Machine Scheduling for Energy Demand Forecasting.
Orchestrates data preparation, time-series split, XGBoost Regressor training, model evaluation,
prediction generation, visualization exporting, and performance report generation.
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root directory to python module search path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config, config
from utils.logger import setup_logger
from preprocessing.loader import DataLoader
from main_phase1 import run_phase_1_pipeline
from forecasting.data_prep import DataPreparer
from forecasting.trainer import ForecastingTrainer
from forecasting.evaluator import ForecastingEvaluator
from forecasting.predictor import ForecastingPredictor
from forecasting.visualizer import ForecastVisualizer
from forecasting.report_generator import ForecastReportGenerator

# Initialize logger instance for Phase 2
logger = setup_logger("SmartSchedulingPhase2", log_file=Config.LOGS_OUTPUT_DIR / "forecasting.log")


def run_phase_2_pipeline() -> None:
    """Executes complete Phase 2 Energy Demand Forecasting pipeline."""
    logger.info("======================================================================")
    logger.info("Starting Phase 2 Execution: Energy Demand Forecasting System (XGBoost)")
    logger.info("======================================================================")

    # Step 1: Ensure directory structure exists
    Config.create_directories()

    # Step 2: Ensure processed dataset is available
    engineered_csv_path = Config.PROCESSED_DATA_DIR / Config.ENERGY_ENGINEERED_FILENAME
    if not engineered_csv_path.exists():
        logger.info(f"Engineered dataset not found at {engineered_csv_path}. Running Phase 1 pipeline first...")
        run_phase_1_pipeline()

    logger.info(f"Loading processed feature-engineered energy dataset from: {engineered_csv_path}")
    df_engineered = pd.read_csv(engineered_csv_path)

    # Step 3: Data Preparation & Time-Series Chronological Split
    logger.info("Step 1/6: Preparing features and executing chronological train/test split...")
    preparer = DataPreparer(cfg=config)
    (
        X_train,
        y_train,
        X_test,
        y_test,
        dates_train,
        dates_test,
    ) = preparer.prepare_data(df_engineered)

    # Save preprocessor artifact
    preparer.save_preprocessor(Config.PREPROCESSOR_OUTPUT_PATH)

    # Step 4: Model Training (XGBoost)
    logger.info("Step 2/6: Training XGBoost Regressor model...")
    trainer = ForecastingTrainer(cfg=config)
    forecaster = trainer.train(
        X_train=X_train,
        y_train=y_train,
        X_val=X_test,
        y_val=y_test,
        model_save_path=Config.MODEL_OUTPUT_PATH,
    )

    # Step 5: Model Evaluation
    logger.info("Step 3/6: Evaluating model predictions on test evaluation set...")
    y_pred_test = forecaster.predict(X_test)
    evaluator = ForecastingEvaluator()
    metrics = evaluator.evaluate(y_true=y_test, y_pred=y_pred_test)

    # Step 6: Prediction Generation & Export
    logger.info("Step 4/6: Exporting test predictions and generating 24h future energy forecast...")
    predictor = ForecastingPredictor(forecaster=forecaster, cfg=config)
    predictions_df = predictor.predict_test_set(
        X_test=X_test,
        y_test=y_test,
        dates_test=dates_test,
        save_path=Config.PREDICTIONS_CSV_PATH,
    )

    # Future 24h prediction (96 steps) for Phase 3
    last_known_row = X_test.iloc[[-1]]
    last_timestamp = pd.to_datetime(dates_test.iloc[-1])
    future_forecast_df = predictor.forecast_future_horizon(
        last_known_row=last_known_row,
        last_timestamp=last_timestamp,
        steps=Config.FUTURE_FORECAST_STEPS,
        save_path=Config.FUTURE_FORECAST_CSV_PATH,
    )

    # Step 7: Feature Importance Extraction
    logger.info("Step 5/6: Extracting feature importances...")
    fi_df = forecaster.get_feature_importance(preparer.feature_columns)

    # Step 8: Forecast Visualizations
    logger.info("Step 6/6: Generating forecast visualization suite...")
    visualizer = ForecastVisualizer(output_dir=Config.FORECAST_OUTPUT_DIR)
    visualizer.generate_all_plots(
        predictions_df=predictions_df,
        feature_importance_df=fi_df,
        future_forecast_df=future_forecast_df,
    )

    # Step 9: Report Generation
    logger.info("Writing comprehensive markdown forecasting report...")
    report_gen = ForecastReportGenerator(cfg=config)
    report_gen.generate_report(
        metrics=metrics,
        feature_importance_df=fi_df,
        train_count=len(X_train),
        test_count=len(X_test),
        train_start=dates_train.iloc[0],
        train_end=dates_train.iloc[-1],
        test_start=dates_test.iloc[0],
        test_end=dates_test.iloc[-1],
    )

    logger.info("======================================================================")
    logger.info("PHASE 2 EXECUTION COMPLETE SUCCESSFULLY!")
    logger.info(f"Model Artifact:    {Config.MODEL_OUTPUT_PATH}")
    logger.info(f"Predictions CSV:   {Config.PREDICTIONS_CSV_PATH}")
    logger.info(f"Forecast Figures:  {Config.FORECAST_OUTPUT_DIR}")
    logger.info(f"Summary Report:    {Config.REPORTS_OUTPUT_DIR / 'forecasting_report.md'}")
    logger.info("Ready for Phase 3: Machine Scheduling & Energy Cost Optimization.")
    logger.info("======================================================================")


if __name__ == "__main__":
    run_phase_2_pipeline()
