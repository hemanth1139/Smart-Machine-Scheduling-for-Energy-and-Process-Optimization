import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from main_phase3 import run_phase_3_pipeline
import pandas as pd

def main():
    print("Running Phase 3 pipeline with updated CP-SAT optimizer...")
    run_phase_3_pipeline()

    comp_path = Path("outputs/scheduling/comparison_report.csv")
    if comp_path.exists():
        df = pd.read_csv(comp_path)
        print("\n=== UPDATED COMPARISON REPORT TABLE ===")
        print(df.to_string())

if __name__ == "__main__":
    main()
