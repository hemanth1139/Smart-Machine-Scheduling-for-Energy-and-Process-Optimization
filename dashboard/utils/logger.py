"""
Dashboard Logger Module.
Provides logging for Streamlit dashboard startup, data loading, user filters, and export operations.
"""

from utils.logger import get_logger, setup_logger
from config.config import Config

# Initialize dashboard logger instance writing to outputs/logs/dashboard.log
dash_logger = setup_logger(
    name="SmartSchedulingDashboard",
    log_file=Config.LOGS_OUTPUT_DIR / "dashboard.log"
)
