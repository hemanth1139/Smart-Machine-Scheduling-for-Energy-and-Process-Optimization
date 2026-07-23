"""
Automated Test for Config Module.
"""

from config.config import Config, config


def test_config_paths():
    """Verifies relative pathlib path resolutions and directory creation."""
    Config.create_directories()
    assert Config.PROJECT_ROOT.exists()
    assert Config.DATA_DIR.exists()
    assert Config.OUTPUTS_DIR.exists()
    assert Config.MODELS_DIR.exists()
    assert Config.LOGS_OUTPUT_DIR.exists()


def test_config_constants():
    """Verifies global configuration constants."""
    assert Config.RANDOM_SEED == 42
    assert Config.SLOT_DURATION_MIN == 15
    assert Config.SCHEDULING_HORIZON_SLOTS == 96
    assert Config.TRAIN_TEST_SPLIT_RATIO == 0.8
