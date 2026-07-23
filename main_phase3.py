"""
Main Entry Point for Phase 3: AI-Based Smart Machine Scheduling & Energy Optimization.
Orchestrates job & machine loading, Phase 2 forecast rate ingestion, FCFS baseline scheduling,
Google OR-Tools CP-SAT multi-objective optimization, KPI calculation, visualization, and report export.
"""

import sys
from pathlib import Path

# Add project root directory to python module search path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config, config
from utils.logger import setup_logger
from main_phase2 import run_phase_2_pipeline
from scheduler.data_loader import SchedulingDataLoader
from scheduler.fcfs import FCFSScheduler
from scheduler.optimizer import OrtoolsScheduler
from scheduler.kpi import KPICalculator
from scheduler.visualization import SchedulingVisualizer
from scheduler.export import SchedulingExporter

# Initialize logger instance for Phase 3
logger = setup_logger("SmartSchedulingPhase3", log_file=Config.LOGS_OUTPUT_DIR / "scheduling.log")


def run_phase_3_pipeline() -> None:
    """Executes complete Phase 3 Machine Scheduling & Energy Cost Optimization pipeline."""
    logger.info("======================================================================")
    logger.info("Starting Phase 3 Execution: Intelligent Machine Scheduling Engine")
    logger.info("======================================================================")

    # Step 1: Ensure directory structure exists
    Config.create_directories()

    # Step 2: Ensure Phase 2 forecasting outputs exist
    forecast_path = Config.FUTURE_FORECAST_CSV_PATH
    if not forecast_path.exists():
        logger.info(f"Forecast output not found at {forecast_path}. Running Phase 2 pipeline first...")
        run_phase_2_pipeline()

    # Step 3: Load Datasets (Jobs, Machines, Predicted Energy Rates)
    logger.info("Step 1/6: Loading Job specifications, Machine parameters, and Energy Rates...")
    data_loader = SchedulingDataLoader(cfg=config)
    parsed_jobs, base_ts = data_loader.load_jobs()
    parsed_machines = data_loader.load_machines()
    energy_rates = data_loader.load_energy_rates()

    # Step 4: Run Baseline First-Come-First-Served (FCFS) Scheduler
    logger.info("Step 2/6: Executing baseline FCFS scheduler for benchmark comparison...")
    fcfs_scheduler = FCFSScheduler(cfg=config)
    fcfs_df = fcfs_scheduler.solve(jobs=parsed_jobs, machines=parsed_machines, energy_rates=energy_rates)

    kpi_calculator = KPICalculator(cfg=config)
    fcfs_kpis = kpi_calculator.compute_kpis(schedule_df=fcfs_df, machines=parsed_machines, energy_rates=energy_rates)

    # Step 5: Run Google OR-Tools CP-SAT Optimized Scheduler
    logger.info("Step 3/6: Executing Google OR-Tools CP-SAT multi-objective optimizer...")
    ortools_scheduler = OrtoolsScheduler(cfg=config)
    opt_df = ortools_scheduler.solve(jobs=parsed_jobs, machines=parsed_machines, energy_rates=energy_rates)

    opt_kpis = kpi_calculator.compute_kpis(schedule_df=opt_df, machines=parsed_machines, energy_rates=energy_rates)

    # Step 6: Generate Visual Analytics Suite (7 Plots)
    logger.info("Step 4/6: Generating scheduling visual analytics suite (Gantt, Timelines, Utilizations)...")
    visualizer = SchedulingVisualizer(output_dir=Config.SCHEDULING_OUTPUT_DIR)
    visualizer.generate_all_plots(
        opt_df=opt_df,
        fcfs_df=fcfs_df,
        opt_kpis=opt_kpis,
        fcfs_kpis=fcfs_kpis,
    )

    # Step 7: Export Schedules, KPI Summary & Comparison Reports
    logger.info("Step 5/6: Exporting schedule CSV files and comparison matrices...")
    exporter = SchedulingExporter(cfg=config)
    export_paths = exporter.export_schedules_and_kpis(
        opt_df=opt_df,
        fcfs_df=fcfs_df,
        opt_kpis=opt_kpis,
        fcfs_kpis=fcfs_kpis,
    )

    logger.info("Step 6/6: Writing comprehensive markdown scheduling report...")
    report_path = exporter.generate_markdown_report(
        opt_kpis=opt_kpis,
        fcfs_kpis=fcfs_kpis,
    )

    cost_saved = fcfs_kpis.get("Total_Energy_Cost_$", 0) - opt_kpis.get("Total_Energy_Cost_$", 0)
    pct_saved = (cost_saved / max(1, fcfs_kpis.get("Total_Energy_Cost_$", 1))) * 100.0

    logger.info("======================================================================")
    logger.info("PHASE 3 EXECUTION COMPLETE SUCCESSFULLY!")
    logger.info(f"Optimized Schedule CSV: {export_paths['opt_schedule']}")
    logger.info(f"FCFS Baseline CSV:     {export_paths['fcfs_schedule']}")
    logger.info(f"KPI Summary CSV:       {export_paths['kpi_summary']}")
    logger.info(f"Comparison Matrix:     {export_paths['comparison']}")
    logger.info(f"Scheduling Figures:    {Config.SCHEDULING_OUTPUT_DIR}")
    logger.info(f"Summary Report:        {report_path}")
    logger.info(f"Total Electricity Cost Savings: ₹{cost_saved:.2f} ({pct_saved:.1f}% reduction)")
    logger.info("Ready for Phase 4: Interactive Web Dashboard & Decision Support System.")
    logger.info("======================================================================")


if __name__ == "__main__":
    run_phase_3_pipeline()
