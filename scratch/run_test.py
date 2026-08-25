import traceback
import sys
import pandas as pd
import numpy as np
import logging

from backend.config import config
from backend.preprocessing import DataLoader, DataCleaner, FeatureEngineer, DataPreparer
from backend.forecasting import MultiQuantileForecaster, ForecastingPredictor
from backend.scheduler import solve_cpsat_scheduler, solve_edf_scheduler
from backend.utils import setup_logger

def log(msg):
    print(msg)
    with open("scratch/scratch_debug.log", "a") as f:
        f.write(msg + "\n")

def run_test():
    # Setup loggers to output to scratch/scratch_debug.log
    log_file = "scratch/scratch_debug.log"
    with open(log_file, "w") as f:
        f.write("--- Starting Debug Run ---\n")
        
    setup_logger("backend.scheduler", log_file=None, level=logging.DEBUG)
    setup_logger("SmartSchedulingPipeline", log_file=None, level=logging.DEBUG)
    
    # Also redirect root logger to scratch_debug.log
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")]
    )
    
    # Add a handler for the scheduler logger to write to log_file
    sched_logger = logging.getLogger("backend.scheduler")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    sched_logger.addHandler(file_handler)
    sched_logger.setLevel(logging.DEBUG)
    
    try:
        log("Loading and cleaning data...")
        raw_energy = DataLoader.load_energy_data()
        raw_jobs = DataLoader.load_job_data()
        raw_machines = DataLoader.load_machine_data()
        
        energy_cleaned = DataCleaner.clean_energy_data(raw_energy)
        jobs_cleaned = DataCleaner.clean_job_data(raw_jobs)
        machines_cleaned = DataCleaner.clean_machine_data(raw_machines)
        
        fe = FeatureEngineer()
        energy_engineered = fe.transform(energy_cleaned)
        
        preparer = DataPreparer()
        X_train, y_train, X_test, y_test, dates_train, dates_test = preparer.prepare_data(energy_engineered)
        
        log("Training forecaster...")
        forecaster = MultiQuantileForecaster()
        forecaster.fit(X_train, y_train)
        
        predictor = ForecastingPredictor(forecaster)
        last_known_row = X_test.iloc[[-1]]
        last_timestamp = pd.to_datetime(dates_test.iloc[-1])
        future_forecast = predictor.forecast_future_horizon(last_known_row, last_timestamp, steps=config.SCHEDULING_HORIZON_SLOTS)
        future_forecast["predicted_kWh"] = future_forecast["predicted_kWh_p50"]
        
        log("Attempting to run solve_cpsat_scheduler Model 1...")
        raw_robust_schedule = solve_cpsat_scheduler(jobs_cleaned, machines_cleaned, future_forecast, robust=True)
        log(f"Successfully completed Model 1! Output length: {len(raw_robust_schedule)}")
    except Exception as e:
        log("CRITICAL ERROR ENCOUNTERED:")
        tb = traceback.format_exc()
        log(tb)
        sys.exit(1)

if __name__ == "__main__":
    run_test()
