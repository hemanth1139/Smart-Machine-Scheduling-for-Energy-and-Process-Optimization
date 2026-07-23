"""
Logging utility for pipeline monitoring and execution tracking.
Configures both file and stream logging with standardized formats.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from config.config import Config


def setup_logger(
    name: str = "SmartSchedulingPipeline",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Configures and returns a logger instance with console and file handlers.

    Args:
        name: Name of the logger instance.
        log_file: Path to log file. Defaults to outputs/logs/pipeline.log if None.
        level: Logging severity level (e.g. logging.INFO).

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already initialized
    if logger.hasHandlers():
        return logger

    # Ensure log output directory exists
    if log_file is None:
        Config.create_directories()
        log_file = Config.LOGS_OUTPUT_DIR / "pipeline.log"

    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Standardized Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "SmartSchedulingPipeline") -> logging.Logger:
    """Retrieves an existing logger or initializes a default logger instance."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        return setup_logger(name)
    return logger
