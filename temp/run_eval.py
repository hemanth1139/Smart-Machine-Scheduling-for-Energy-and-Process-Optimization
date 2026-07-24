import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from main_phase3 import run_phase_3_pipeline
import pandas as pd

if __name__ == "__main__":
    run_phase_3_pipeline()
    comp_df = pd.read_csv(project_root / "outputs" / "scheduling" / "comparison_report.csv")
    print("\n--- SCHEDULING COMPARISON MATRIX ---")
    print(comp_df.to_string())
