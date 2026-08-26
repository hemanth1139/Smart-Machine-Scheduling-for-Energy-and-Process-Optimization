"""
Orchestration Pipeline for the Predict-then-Optimize Scheduling Framework.
Executes Phase 1 (Preprocessing), Phase 2 (Forecasting), and Phase 3 (Benchmarking Schedulers).
Generates Streamlit-compatible outputs in data/processed and output/ directories.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.config import config
from backend.preprocessing import DataLoader, DataCleaner, FeatureEngineer, DataPreparer
from backend.forecasting import MultiQuantileForecaster, ForecastingPredictor
from backend.scheduler import (
    solve_proposed_scheduler,
    solve_deterministic_scheduler,
    solve_makespan_scheduler,
    solve_edf_scheduler,
    solve_fcfs_scheduler,
    solve_hybrid_scheduler,
)
from backend.kpi_calculator import compute_schedule_kpis
from backend.utils import setup_logger
from backend.generate_dataset import generate_datasets

logger = setup_logger("SmartSchedulingPipeline", log_file=project_root / "pipeline.log")


def enrich_schedule(schedule_df: pd.DataFrame, jobs_df: pd.DataFrame, machines_df: pd.DataFrame, forecast_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches a raw schedule dataframe with priority mapping, time string formatting,
    delays, and active energy costs per job to match frontend page rendering needs.
    """
    if schedule_df.empty:
        return pd.DataFrame()
        
    job_map = jobs_df.set_index("Job_ID").to_dict(orient="index")
    mach_map = machines_df.set_index("Machine_ID").to_dict(orient="index")
    
    # Cyclic tariffs so jobs beyond the forecast window are priced fairly
    base_n = max(1, len(forecast_df))
    base_tariffs = np.zeros(base_n)
    for t in range(base_n):
        load_type = forecast_df.iloc[t].get("Load_Type", "Light_Load")
        if load_type == "Maximum_Load":
            base_tariffs[t] = config.TARIFF_MAX_LOAD
        elif load_type == "Medium_Load":
            base_tariffs[t] = config.TARIFF_MED_LOAD
        else:
            base_tariffs[t] = config.TARIFF_LIGHT_LOAD

    enriched_rows = []
    for _, row in schedule_df.iterrows():
        jid = row["Job_ID"]
        mid = row["Machine_ID"]
        start_slot = int(row["Start_Slot"])
        end_slot = int(row["End_Slot"])
        
        j_p = job_map[jid]
        m_p = mach_map[mid]
        
        # Calculate active energy cost (cyclic tariff extension)
        active_power = m_p["Active_Power_kW"]
        job_cost = 0.0
        for t in range(start_slot, end_slot):
            job_cost += active_power * 0.25 * base_tariffs[t % base_n]
            
        # Add setup cost (setup energy * tariff at start slot)
        setup_energy = m_p["Setup_Energy_kW"]
        job_cost += setup_energy * 0.25 * base_tariffs[start_slot % base_n]
        
        # Format times (HH:MM relative to 00:00 start)
        start_min = start_slot * 15
        end_min = end_slot * 15
        start_time_str = f"{start_min // 60:02d}:{start_min % 60:02d}"
        end_time_str = f"{end_min // 60:02d}:{end_min % 60:02d}"
        
        # Delay
        deadline_slot = j_p["Deadline"]
        delay_slots = max(0, end_slot - deadline_slot)
        delay_min = delay_slots * 15
        
        # Priority mapping
        priority_map = {1: "High", 2: "Medium", 3: "Low"}
        priority_str = priority_map.get(int(j_p["Priority"]), "Low")
        
        enriched_rows.append({
            "Job_ID": jid,
            "Machine_ID": mid,
            "Assigned_Machine": mid,
            "Machine_Type": m_p["Machine_Type"],
            "Start_Slot": start_slot,
            "End_Slot": end_slot,
            "Start_Time": start_time_str,
            "End_Time": end_time_str,
            "Duration_min": (end_slot - start_slot) * 15,
            "Priority": priority_str,
            "Delay_min": delay_min,
            "Energy_Cost_$": round(job_cost, 2),
            "Is_Late": 1 if end_slot > deadline_slot else 0
        })
        
    return pd.DataFrame(enriched_rows)


def main():
    logger.info("Initializing Predict-then-Optimize End-to-End Pipeline...")
    config.create_directories()
    
    # ----------------------------------------------------
    # STEP 0: Generate Synthetic Datasets
    # ----------------------------------------------------
    logger.info("Step 0/5: Generating synthetic job and machine datasets...")
    generate_datasets()
    logger.info("Datasets generated successfully.")
    
    # ----------------------------------------------------
    # STEP 1: Preprocessing & Cleaning (Phase 1)
    # ----------------------------------------------------
    logger.info("Step 1/5: Running Data cleaning and feature engineering...")
    
    # Load
    raw_energy = DataLoader.load_energy_data()
    raw_jobs = DataLoader.load_job_data()
    raw_machines = DataLoader.load_machine_data()
    
    # Clean
    energy_cleaned = DataCleaner.clean_energy_data(raw_energy)
    jobs_cleaned = DataCleaner.clean_job_data(raw_jobs)
    machines_cleaned = DataCleaner.clean_machine_data(raw_machines)
    
    # Feature Engineer
    fe = FeatureEngineer()
    energy_engineered = fe.transform(energy_cleaned)
    
    # Save Cleaned / Processed
    jobs_cleaned.to_csv(config.PROCESSED_DATA_DIR / "jobs_cleaned.csv", index=False)
    machines_cleaned.to_csv(config.PROCESSED_DATA_DIR / "machines_cleaned.csv", index=False)
    energy_engineered.to_csv(config.PROCESSED_DATA_DIR / "energy_engineered.csv", index=False)
    
    logger.info("Data preprocessing completed successfully.")
    
    # ----------------------------------------------------
    # STEP 2: Multi-Target Multi-Quantile Forecasting (Phase 2)
    # ----------------------------------------------------
    logger.info("Step 2/5: Preparing features and training Quantile XGBoost forecaster...")
    
    preparer = DataPreparer()
    X_train, y_train, X_test, y_test, dates_train, dates_test = preparer.prepare_data(energy_engineered)
    preparer.save_preprocessor(config.MODELS_DIR / "preprocessor.joblib")
    
    # Train
    forecaster = MultiQuantileForecaster()
    forecaster.fit(X_train, y_train)
    forecaster.save(config.MODELS_DIR / "energy_xgb_model.joblib")
    
    # Predict on test set
    predictor = ForecastingPredictor(forecaster)
    test_preds = predictor.predict_test_set(X_test, y_test, dates_test)
    
    # Forecast future shift (48 hours = SCHEDULING_HORIZON_SLOTS steps)
    last_known_row = X_test.iloc[[-1]]
    last_timestamp = pd.to_datetime(dates_test.iloc[-1])
    future_forecast = predictor.forecast_future_horizon(last_known_row, last_timestamp, steps=config.SCHEDULING_HORIZON_SLOTS)
    
    # Map p50 forecast to predicted_kWh so Streamlit page loads it directly
    future_forecast["predicted_kWh"] = future_forecast["predicted_kWh_p50"]
    future_forecast.to_csv(config.OUTPUT_DIR / "future_forecast.csv", index=False)
    
    logger.info("Forecasting and model persistence completed.")
    
    # ----------------------------------------------------
    # STEP 3: Scheduling Optimization Benchmarks
    # ----------------------------------------------------
    logger.info("Step 3/5: Running Scheduling Optimization Benchmark algorithms...")
    
    # 1. Proposed: Robust Energy-Aware Greedy (uses p90 tariff forecast)
    logger.info("Solving Model 1: Proposed Robust Energy-Aware Greedy...")
    raw_robust_schedule = solve_proposed_scheduler(jobs_cleaned, machines_cleaned, future_forecast, use_robust=True)
    robust_schedule = enrich_schedule(raw_robust_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    robust_schedule.to_csv(config.OUTPUT_DIR / "robust_schedule.csv", index=False)
    logger.info(f"Model 1 done: {len(raw_robust_schedule)} jobs scheduled.")
    
    # 2. Deterministic Energy-Aware Greedy (uses p50 only)
    logger.info("Solving Model 2: Deterministic Energy-Aware Greedy (p50 baseline)...")
    raw_deterministic_schedule = solve_deterministic_scheduler(jobs_cleaned, machines_cleaned, future_forecast)
    deterministic_schedule = enrich_schedule(raw_deterministic_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    deterministic_schedule.to_csv(config.OUTPUT_DIR / "deterministic_schedule.csv", index=False)
    logger.info(f"Model 2 done: {len(raw_deterministic_schedule)} jobs scheduled.")
    
    # 3. Makespan-Only Greedy
    logger.info("Solving Model 3: Makespan-Only Greedy...")
    raw_makespan_schedule = solve_makespan_scheduler(jobs_cleaned, machines_cleaned, future_forecast)
    makespan_schedule = enrich_schedule(raw_makespan_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    makespan_schedule.to_csv(config.OUTPUT_DIR / "makespan_schedule.csv", index=False)
    logger.info(f"Model 3 done: {len(raw_makespan_schedule)} jobs scheduled.")
    
    # 4. EDF Baseline
    logger.info("Solving Model 4: Earliest Deadline First (EDF)...")
    raw_edf_schedule = solve_edf_scheduler(jobs_cleaned, machines_cleaned, future_forecast)
    edf_schedule = enrich_schedule(raw_edf_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    edf_schedule.to_csv(config.OUTPUT_DIR / "edf_schedule.csv", index=False)
    logger.info(f"Model 4 done: {len(raw_edf_schedule)} jobs scheduled.")
    
    # 5. FCFS Baseline
    logger.info("Solving Model 5: First Come First Served (FCFS)...")
    raw_fcfs_schedule = solve_fcfs_scheduler(jobs_cleaned, machines_cleaned, future_forecast)
    fcfs_schedule = enrich_schedule(raw_fcfs_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    fcfs_schedule.to_csv(config.OUTPUT_DIR / "fcfs_schedule.csv", index=False)
    logger.info(f"Model 5 done: {len(raw_fcfs_schedule)} jobs scheduled.")
    
    # 6. Hybrid: FD-PDTS warm-start + CP-SAT refinement
    logger.info("Solving Model 6: Hybrid FD-PDTS + CP-SAT (warm-start refinement)...")
    raw_hybrid_schedule = solve_hybrid_scheduler(jobs_cleaned, machines_cleaned, future_forecast)
    hybrid_schedule = enrich_schedule(raw_hybrid_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    hybrid_schedule.to_csv(config.OUTPUT_DIR / "hybrid_schedule.csv", index=False)
    hybrid_schedule.to_csv(config.OUTPUT_DIR / "optimized_schedule.csv", index=False)
    logger.info(f"Model 6 done: {len(raw_hybrid_schedule)} jobs scheduled.")
    
    logger.info("All scheduling runs completed successfully.")
    
    # ----------------------------------------------------
    # STEP 4: KPI Computation & Benchmarking (Phase 3)
    # ----------------------------------------------------
    logger.info("Step 4/5: Computing KPIs for all benchmark models...")
    
    kpis_robust   = compute_schedule_kpis(raw_robust_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    kpis_det      = compute_schedule_kpis(raw_deterministic_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    kpis_makespan = compute_schedule_kpis(raw_makespan_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    kpis_edf      = compute_schedule_kpis(raw_edf_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    kpis_fcfs     = compute_schedule_kpis(raw_fcfs_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    kpis_hybrid   = compute_schedule_kpis(raw_hybrid_schedule, jobs_cleaned, machines_cleaned, future_forecast)
    
    # Save kpi_summary.csv for Streamlit metric scorecards
    kpi_summary = pd.DataFrame([
        {
            "Schedule_Type": "CP_SAT_Optimized",
            "Total_Energy_Cost_$": kpis_hybrid["Total_Energy_Cost_INR"],
            "Peak_Hour_Load_kWh": kpis_hybrid["Peak_Hour_Load_kW"],
            "Machine_Utilization_%": kpis_hybrid["Machine_Utilization_pct"],
            "Average_Waiting_Time_min": kpis_hybrid["Average_Waiting_Time_min"],
            "Number_of_Late_Jobs": kpis_hybrid["Late_Jobs"],
            "On_Time_Completion_%": kpis_hybrid["On_Time_Completion_pct"]
        },
        {
            "Schedule_Type": "Baseline_FCFS",
            "Total_Energy_Cost_$": kpis_fcfs["Total_Energy_Cost_INR"],
            "Peak_Hour_Load_kWh": kpis_fcfs["Peak_Hour_Load_kW"],
            "Machine_Utilization_%": kpis_fcfs["Machine_Utilization_pct"],
            "Average_Waiting_Time_min": kpis_fcfs["Average_Waiting_Time_min"],
            "Number_of_Late_Jobs": kpis_fcfs["Late_Jobs"],
            "On_Time_Completion_%": kpis_fcfs["On_Time_Completion_pct"]
        }
    ])
    kpi_summary.to_csv(config.OUTPUT_DIR / "kpi_summary.csv", index=False)
    
    # Generate HTML-compatible comparison CSV
    # Columns required by Streamlit dashboard: Metric, FCFS_Baseline, CP_SAT_Optimized, Improvement
    comp_metrics = [
        ("Total Energy Cost (INR)", "Total_Energy_Cost_INR", "₹{:.2f}", "₹{:.2f}", "lower"),
        ("Peak Grid Load (kW)", "Peak_Hour_Load_kW", "{:.2f} kW", "{:.2f} kW", "lower"),
        ("Makespan (hours)", "Makespan_hours", "{:.2f} hrs", "{:.2f} hrs", "lower"),
        ("Machine Utilization (%)", "Machine_Utilization_pct", "{:.2f}%", "{:.2f}%", "higher"),
        ("Average Waiting Time (min)", "Average_Waiting_Time_min", "{:.1f} min", "{:.1f} min", "lower"),
        ("Total Idle Time (min)", "Total_Idle_Time_min", "{:.1f} min", "{:.1f} min", "lower"),
        ("Total Delay (min)", "Total_Delay_min", "{:.1f} min", "{:.1f} min", "lower"),
        ("Late Jobs (count)", "Late_Jobs", "{:d} jobs", "{:d} jobs", "lower"),
        ("On-Time Completion (%)", "On_Time_Completion_pct", "{:.2f}%", "{:.2f}%", "higher"),
        ("Carbon Emissions (tCO2)", "Total_Carbon_Emissions_tCO2", "{:.4f} t", "{:.4f} t", "lower"),
        ("Power Factor Penalty (INR)", "Total_Power_Factor_Penalty_INR", "₹{:.2f}", "₹{:.2f}", "lower")
    ]
    
    comparison_data = []
    for label, key, fmt_fcfs, fmt_opt, goal in comp_metrics:
        val_fcfs = kpis_fcfs[key]
        val_opt = kpis_hybrid[key]
        
        # Improvement string calculation
        if goal == "lower":
            diff = val_fcfs - val_opt
            if val_fcfs > 0:
                pct_change = (diff / val_fcfs) * 100
                imp_str = f"{diff:.2f} reduction ({pct_change:.1f}% savings)" if diff > 0 else f"+{abs(diff):.2f} ({abs(pct_change):.1f}% increase)"
            else:
                imp_str = f"{diff:.2f} reduction" if diff > 0 else f"+{abs(diff):.2f} increase"
        else:
            diff = val_opt - val_fcfs
            if val_fcfs > 0:
                pct_change = (diff / val_fcfs) * 100
                imp_str = f"+{diff:.2f}% improvement ({pct_change:.1f}% gain)" if diff > 0 else f"{diff:.2f}% reduction"
            else:
                imp_str = f"+{diff:.2f}% improvement" if diff > 0 else f"{diff:.2f}% reduction"
                
        # Clean up some specific labels
        if key == "Late_Jobs" and diff == val_fcfs and val_opt == 0:
            imp_str = "Zero delays (100% savings)"
        if key == "Total_Power_Factor_Penalty_INR" and val_fcfs == 0 and val_opt == 0:
            imp_str = "No Penalties Incurred"
            
        comparison_data.append({
            "Metric": label,
            "FCFS_Baseline": fmt_fcfs.format(val_fcfs),
            "CP_SAT_Optimized": fmt_opt.format(val_opt),
            "Improvement": imp_str
        })
        
    comp_df = pd.DataFrame(comparison_data)
    comp_df.to_csv(config.OUTPUT_DIR / "comparison_report.csv", index=False)

    # Generate a comprehensive publication-ready report of all 6 algorithms
    all_kpis = {
        "FCFS": kpis_fcfs,
        "EDF": kpis_edf,
        "Makespan_Greedy": kpis_makespan,
        "Proposed_Robust_Greedy": kpis_robust,
        "Deterministic_Greedy": kpis_det,
        "Hybrid_Solver": kpis_hybrid
    }
    
    comprehensive_rows = []
    for label, key, _, _, _ in comp_metrics:
        row = {"Metric": label}
        for name, model_kpis in all_kpis.items():
            val = model_kpis[key]
            if "Cost" in label or "Penalty" in label:
                row[name] = f"INR {val:.2f}"
            elif "Load" in label:
                row[name] = f"{val:.2f} kW"
            elif "Makespan" in label:
                row[name] = f"{val:.2f} hrs"
            elif "Utilization" in label or "On-Time" in label:
                row[name] = f"{val:.2f}%"
            elif "Emissions" in label:
                row[name] = f"{val:.4f} t"
            elif "Late" in label:
                row[name] = f"{int(val)} jobs"
            else:
                row[name] = f"{val:.1f} min"
        comprehensive_rows.append(row)
        
    comprehensive_df = pd.DataFrame(comprehensive_rows)
    comprehensive_df.to_csv(config.OUTPUT_DIR / "comprehensive_report.csv", index=False)
    logger.info("Saved comprehensive benchmark comparison report to output/comprehensive_report.csv")
    
    logger.info("======================================================================")
    logger.info("BENCHMARK RESULTS SUMMARY:")
    logger.info("======================================================================")
    # Write summary to log file to avoid Windows console encoding issues
    summary_str = comp_df.to_string(index=False).replace("\u20b9", "INR ")
    for line in summary_str.split("\n"):
        logger.info(line)
    logger.info("======================================================================")
    
    logger.info("Pipeline executed successfully. Outputs written to output/ directory.")


if __name__ == "__main__":
    main()
