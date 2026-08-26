"""Quick full-model benchmark and report refresh (skips XGBoost)."""
import pandas as pd
from backend.config import config
from backend.preprocessing import DataLoader, DataCleaner
from backend.scheduler import (
    solve_fcfs_scheduler,
    solve_edf_scheduler,
    solve_makespan_scheduler,
    solve_proposed_scheduler,
    solve_deterministic_scheduler,
    solve_hybrid_scheduler,
)
from backend.kpi_calculator import compute_schedule_kpis
from run_pipeline import enrich_schedule

jobs = DataCleaner.clean_job_data(DataLoader.load_job_data())
machines = DataCleaner.clean_machine_data(DataLoader.load_machine_data())
fcst = pd.read_csv("output/future_forecast.csv")

raw = {
    "FCFS": solve_fcfs_scheduler(jobs, machines, fcst),
    "EDF": solve_edf_scheduler(jobs, machines, fcst),
    "Makespan_Greedy": solve_makespan_scheduler(jobs, machines, fcst),
    "Proposed_Robust_Greedy": solve_proposed_scheduler(jobs, machines, fcst, True),
    "Deterministic_Greedy": solve_deterministic_scheduler(jobs, machines, fcst),
    "Hybrid_Solver": solve_hybrid_scheduler(jobs, machines, fcst),
}

file_map = {
    "FCFS": "fcfs_schedule.csv",
    "EDF": "edf_schedule.csv",
    "Makespan_Greedy": "makespan_schedule.csv",
    "Proposed_Robust_Greedy": "robust_schedule.csv",
    "Deterministic_Greedy": "deterministic_schedule.csv",
    "Hybrid_Solver": "hybrid_schedule.csv",
}

all_kpis = {}
for name, sch in raw.items():
    k = compute_schedule_kpis(sch, jobs, machines, fcst)
    all_kpis[name] = k
    print(
        f"{name:24s} cost={k['Total_Energy_Cost_INR']:10.1f} "
        f"peak={k['Peak_Hour_Load_kW']:7.1f} make={k['Makespan_hours']:5.1f} "
        f"wait={k['Average_Waiting_Time_min']:6.1f} "
        f"ontime={k['On_Time_Completion_pct']:5.1f} late={k['Late_Jobs']:3d}"
    )
    enrich_schedule(sch, jobs, machines, fcst).to_csv(
        config.OUTPUT_DIR / file_map[name], index=False
    )

enrich_schedule(raw["Hybrid_Solver"], jobs, machines, fcst).to_csv(
    config.OUTPUT_DIR / "optimized_schedule.csv", index=False
)

comp_metrics = [
    ("Total Energy Cost (INR)", "Total_Energy_Cost_INR"),
    ("Peak Grid Load (kW)", "Peak_Hour_Load_kW"),
    ("Makespan (hours)", "Makespan_hours"),
    ("Machine Utilization (%)", "Machine_Utilization_pct"),
    ("Average Waiting Time (min)", "Average_Waiting_Time_min"),
    ("Total Idle Time (min)", "Total_Idle_Time_min"),
    ("Total Delay (min)", "Total_Delay_min"),
    ("Late Jobs (count)", "Late_Jobs"),
    ("On-Time Completion (%)", "On_Time_Completion_pct"),
    ("Carbon Emissions (tCO2)", "Total_Carbon_Emissions_tCO2"),
    ("Power Factor Penalty (INR)", "Total_Power_Factor_Penalty_INR"),
]

rows = []
for label, key in comp_metrics:
    row = {"Metric": label}
    for name, k in all_kpis.items():
        v = k[key]
        if "Cost" in label or "Penalty" in label:
            row[name] = f"INR {v:.2f}"
        elif "Load" in label:
            row[name] = f"{v:.2f} kW"
        elif "Makespan" in label:
            row[name] = f"{v:.2f} hrs"
        elif "Utilization" in label or "On-Time" in label:
            row[name] = f"{v:.2f}%"
        elif "Emissions" in label:
            row[name] = f"{v:.4f} t"
        elif "Late" in label:
            row[name] = f"{int(v)} jobs"
        else:
            row[name] = f"{v:.1f} min"
    rows.append(row)
pd.DataFrame(rows).to_csv(config.OUTPUT_DIR / "comprehensive_report.csv", index=False)

kf, kh = all_kpis["FCFS"], all_kpis["Hybrid_Solver"]
cdata = []
for label, key in comp_metrics:
    vf, vh = kf[key], kh[key]
    if key in ("Machine_Utilization_pct", "On_Time_Completion_pct"):
        diff = vh - vf
        imp = f"+{diff:.2f}% improvement" if diff > 0 else f"{diff:.2f}% reduction"
    else:
        diff = vf - vh
        pct = (diff / vf * 100) if vf else 0
        imp = (
            f"{diff:.2f} reduction ({pct:.1f}% savings)"
            if diff > 0
            else f"+{abs(diff):.2f} ({abs(pct):.1f}% increase)"
        )
    if key == "Total_Power_Factor_Penalty_INR" and vf == 0 and vh == 0:
        imp = "No Penalties Incurred"
    row = next(r for r in rows if r["Metric"] == label)
    cdata.append(
        {
            "Metric": label,
            "FCFS_Baseline": row["FCFS"],
            "CP_SAT_Optimized": row["Hybrid_Solver"],
            "Improvement": imp,
        }
    )
pd.DataFrame(cdata).to_csv(config.OUTPUT_DIR / "comparison_report.csv", index=False)

pd.DataFrame(
    [
        {
            "Schedule_Type": "CP_SAT_Optimized",
            "Total_Energy_Cost_$": kh["Total_Energy_Cost_INR"],
            "Peak_Hour_Load_kWh": kh["Peak_Hour_Load_kW"],
            "Machine_Utilization_%": kh["Machine_Utilization_pct"],
            "Average_Waiting_Time_min": kh["Average_Waiting_Time_min"],
            "Number_of_Late_Jobs": kh["Late_Jobs"],
            "On_Time_Completion_%": kh["On_Time_Completion_pct"],
        },
        {
            "Schedule_Type": "Baseline_FCFS",
            "Total_Energy_Cost_$": kf["Total_Energy_Cost_INR"],
            "Peak_Hour_Load_kWh": kf["Peak_Hour_Load_kW"],
            "Machine_Utilization_%": kf["Machine_Utilization_pct"],
            "Average_Waiting_Time_min": kf["Average_Waiting_Time_min"],
            "Number_of_Late_Jobs": kf["Late_Jobs"],
            "On_Time_Completion_%": kf["On_Time_Completion_pct"],
        },
    ]
).to_csv(config.OUTPUT_DIR / "kpi_summary.csv", index=False)
print("Reports refreshed.")
