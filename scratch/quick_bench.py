"""Quick scheduling benchmark (no XGBoost / hybrid)."""
from backend.generate_dataset import generate_datasets
generate_datasets()

import pandas as pd
from backend.config import config
from backend.preprocessing import DataLoader, DataCleaner
from backend.scheduler import (
    solve_fcfs_scheduler,
    solve_edf_scheduler,
    solve_makespan_scheduler,
    solve_proposed_scheduler,
    solve_deterministic_scheduler,
)
from backend.kpi_calculator import compute_schedule_kpis

raw_jobs = DataLoader.load_job_data()
raw_machines = DataLoader.load_machine_data()
jobs = DataCleaner.clean_job_data(raw_jobs)
machines = DataCleaner.clean_machine_data(raw_machines)
jobs.to_csv(config.PROCESSED_DATA_DIR / "jobs_cleaned.csv", index=False)
machines.to_csv(config.PROCESSED_DATA_DIR / "machines_cleaned.csv", index=False)
fcst = pd.read_csv("output/future_forecast.csv")

models = {
    "FCFS": solve_fcfs_scheduler,
    "EDF": solve_edf_scheduler,
    "Makespan": solve_makespan_scheduler,
    "Robust": lambda j, m, f: solve_proposed_scheduler(j, m, f, True),
    "Det": solve_deterministic_scheduler,
}

print(f"jobs={len(jobs)} machines={len(machines)}")
for name, fn in models.items():
    sch = fn(jobs, machines, fcst)
    k = compute_schedule_kpis(sch, jobs, machines, fcst)
    print(
        f"{name:10s} cost={k['Total_Energy_Cost_INR']:10.1f} "
        f"peak={k['Peak_Hour_Load_kW']:7.1f} make={k['Makespan_hours']:6.1f}h "
        f"ontime={k['On_Time_Completion_pct']:5.1f}% late={k['Late_Jobs']:3d} "
        f"util={k['Machine_Utilization_pct']:5.1f}% end={int(sch['End_Slot'].max())}"
    )
