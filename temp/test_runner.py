import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import logging
from config.config import config
from utils.logger import setup_logger

logger = setup_logger("SmartSchedulingPhase3", log_file=config.LOGS_OUTPUT_DIR / "scheduling.log")

from main_phase3 import run_phase_3_pipeline
import pandas as pd

if __name__ == "__main__":
    print("Executing Phase 3 Pipeline...")
    run_phase_3_pipeline()

    comp_path = config.SCHEDULING_OUTPUT_DIR / config.COMPARISON_REPORT_FILENAME
    if comp_path.exists():
        df = pd.read_csv(comp_path)
        print("\n================ UPDATED COMPARISON MATRIX ================")
        print(df.to_string())
