"""
Automated Test for DataLoader Module.
"""

from preprocessing.loader import DataLoader
from config.config import config


def test_data_loader_raw():
    """Verifies that DataLoader safely loads all 3 datasets."""
    loader = DataLoader(cfg=config)
    energy_df, job_df, machine_df = loader.load_all()

    assert not energy_df.empty
    assert not job_df.empty
    assert not machine_df.empty

    assert "date" in energy_df.columns or "Usage_kWh" in energy_df.columns
    assert "Job_ID" in job_df.columns
    assert "Machine_ID" in machine_df.columns
