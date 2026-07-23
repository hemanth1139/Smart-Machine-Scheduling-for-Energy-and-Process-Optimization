"""
Main Execution Launcher for Phase 4: Streamlit Interactive Analytics Dashboard.
Checks project outputs and launches the multi-page Streamlit web app.
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config
from utils.logger import setup_logger

logger = setup_logger("SmartSchedulingPhase4")


def run_phase_4_dashboard() -> None:
    """Launches Streamlit Dashboard App."""
    logger.info("======================================================================")
    logger.info("Starting Phase 4 Execution: Streamlit Interactive Analytics Dashboard")
    logger.info("======================================================================")

    app_path = project_root / "dashboard" / "app.py"
    if not app_path.exists():
        logger.error(f"Dashboard entry point not found at: {app_path}")
        return

    logger.info(f"Launching Streamlit Web Application: streamlit run {app_path}")
    logger.info("Access the interactive dashboard in your web browser at: http://localhost:8501")
    logger.info("======================================================================")

    # Launch Streamlit process
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)
    except KeyboardInterrupt:
        logger.info("Dashboard shutdown requested by user.")
    except Exception as e:
        logger.error(f"Error launching Streamlit dashboard: {e}")


if __name__ == "__main__":
    run_phase_4_dashboard()
