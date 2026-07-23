"""
Central Execution Entry Point for AI-Based Smart Machine Scheduling for Energy & Process Optimization.
Orchestrates raw data loading, data validation, cleaning, feature engineering, XGBoost forecasting,
Google OR-Tools CP-SAT machine scheduling, KPI calculation, report generation, testing, and Streamlit UI.
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path

# Add project root directory to python module search path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config, config
from utils.logger import setup_logger

# Import pipeline stage runners
from main_phase1 import run_phase_1_pipeline
from main_phase2 import run_phase_2_pipeline
from main_phase3 import run_phase_3_pipeline

# Initialize primary project logger
logger = setup_logger("SmartMachineSchedulingSystem", log_file=Config.LOGS_OUTPUT_DIR / "pipeline.log")


def run_full_end_to_end_pipeline(force_retrain: bool = False) -> None:
    """
    Executes complete end-to-end pipeline across Phase 1, Phase 2, and Phase 3.

    Args:
        force_retrain: If True, forces retraining of XGBoost forecasting model.
    """
    start_time = time.time()
    logger.info("==================================================================================")
    logger.info("STARTING COMPLETE END-TO-END PIPELINE: SMART MACHINE SCHEDULING & ENERGY AI")
    logger.info("==================================================================================")

    # Ensure output directories exist
    Config.create_directories()

    try:
        # Stage 1: Data Preparation & Preprocessing (Phase 1)
        logger.info("▶ [Stage 1/3] Phase 1: Data Cleaning, Validation & Time-Series Feature Engineering")
        run_phase_1_pipeline()

        # Stage 2: Energy Demand Forecasting (Phase 2)
        logger.info("▶ [Stage 2/3] Phase 2: Time-Series Energy Forecasting (XGBoost Regressor)")
        model_path = Config.MODEL_OUTPUT_PATH
        if force_retrain or not model_path.exists():
            logger.info("Retraining XGBoost energy demand forecasting model...")
            run_phase_2_pipeline()
        else:
            logger.info(f"Existing trained XGBoost model checkpoint found at: {model_path}. Proceeding.")
            run_phase_2_pipeline()

        # Stage 3: Intelligent Machine Scheduling (Phase 3)
        logger.info("▶ [Stage 3/3] Phase 3: Intelligent Machine Scheduling Engine (Google OR-Tools CP-SAT)")
        run_phase_3_pipeline()

        elapsed_sec = round(time.time() - start_time, 2)
        logger.info("==================================================================================")
        logger.info(f"END-TO-END PIPELINE COMPLETED SUCCESSFULLY IN {elapsed_sec} SECONDS!")
        logger.info("Outputs generated in: outputs/forecasting, outputs/scheduling, outputs/reports")
        logger.info("==================================================================================")

    except Exception as e:
        logger.error(f"Fatal error during end-to-end pipeline execution: {e}", exc_info=True)
        raise e


def launch_dashboard() -> None:
    """Launches Phase 4 Streamlit Interactive Analytics Dashboard."""
    app_path = Config.PROJECT_ROOT / "dashboard" / "app.py"
    if not app_path.exists():
        logger.error(f"Dashboard entry point not found at: {app_path}")
        return

    logger.info("==================================================================================")
    logger.info("LAUNCHING PHASE 4 STREAMLIT INTERACTIVE ANALYTICS DASHBOARD")
    logger.info(f"Command: streamlit run {app_path}")
    logger.info("Access the web UI at: http://localhost:8501")
    logger.info("==================================================================================")

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)
    except KeyboardInterrupt:
        logger.info("Streamlit dashboard shut down by user.")
    except Exception as e:
        logger.error(f"Error launching Streamlit dashboard: {e}")


def run_tests() -> None:
    """Executes automated Pytest test suite in tests/."""
    logger.info("==================================================================================")
    logger.info("RUNNING AUTOMATED PYTEST SUITE")
    logger.info("==================================================================================")
    try:
        res = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], check=False)
        if res.returncode == 0:
            logger.info("ALL AUTOMATED TESTS PASSED SUCCESSFULLY!")
        else:
            logger.warning(f"Pytest suite completed with exit code: {res.returncode}")
    except Exception as e:
        logger.error(f"Error running pytest suite: {e}")


def parse_cli_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-Based Smart Machine Scheduling for Energy & Process Optimization System"
    )
    parser.add_argument(
        "--pipeline-only",
        action="store_true",
        help="Executes complete data, forecasting, and scheduling pipeline without launching Streamlit UI.",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Launches Streamlit Interactive Dashboard directly consuming existing output artifacts.",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Forces retraining of the XGBoost energy demand forecasting model.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Runs the automated Pytest test suite in tests/.",
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI Execution Entry Point."""
    args = parse_cli_args()

    if args.test:
        run_tests()
        return

    if args.dashboard_only:
        launch_dashboard()
        return

    if args.pipeline_only:
        run_full_end_to_end_pipeline(force_retrain=args.retrain)
        return

    # Default Behavior: Run full end-to-end pipeline, then launch Streamlit UI
    run_full_end_to_end_pipeline(force_retrain=args.retrain)
    launch_dashboard()


if __name__ == "__main__":
    main()
