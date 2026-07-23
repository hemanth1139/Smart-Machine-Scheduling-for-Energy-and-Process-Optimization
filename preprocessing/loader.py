"""
Data Loading Module.
Loads project datasets (Energy, Job, Machine) using Pandas and non-hardcoded relative paths.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Class responsible for loading raw datasets cleanly."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def load_energy_data(self) -> pd.DataFrame:
        """
        Loads the UCI Steel Industry Energy Consumption Dataset.

        Returns:
            pd.DataFrame: Raw energy consumption dataset.
        """
        file_path = self.cfg.get_raw_path(self.cfg.ENERGY_DATA_FILENAME)
        if not file_path.exists():
            error_msg = f"Energy dataset file not found at: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Loading Energy dataset from: {file_path}")
        df = pd.read_csv(file_path)
        logger.info(f"Energy dataset successfully loaded with shape: {df.shape}")
        return df

    def load_job_data(self) -> pd.DataFrame:
        """
        Loads the Synthetic Job Dataset.

        Returns:
            pd.DataFrame: Job dataset.
        """
        file_path = self.cfg.get_raw_path(self.cfg.JOB_DATA_FILENAME)
        if not file_path.exists():
            error_msg = f"Job dataset file not found at: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Loading Job dataset from: {file_path}")
        df = pd.read_csv(file_path)
        logger.info(f"Job dataset successfully loaded with shape: {df.shape}")
        return df

    def load_machine_data(self) -> pd.DataFrame:
        """
        Loads the Synthetic Machine Dataset.

        Returns:
            pd.DataFrame: Machine dataset.
        """
        file_path = self.cfg.get_raw_path(self.cfg.MACHINE_DATA_FILENAME)
        if not file_path.exists():
            error_msg = f"Machine dataset file not found at: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Loading Machine dataset from: {file_path}")
        df = pd.read_csv(file_path)
        logger.info(f"Machine dataset successfully loaded with shape: {df.shape}")
        return df

    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Loads all three datasets simultaneously.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (energy_df, job_df, machine_df)
        """
        logger.info("Loading all project datasets (Energy, Job, Machine)...")
        energy_df = self.load_energy_data()
        job_df = self.load_job_data()
        machine_df = self.load_machine_data()
        return energy_df, job_df, machine_df
