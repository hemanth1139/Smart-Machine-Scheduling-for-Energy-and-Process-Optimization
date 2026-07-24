"""Run the clearly labelled synthetic energy-optimisation benchmark.

This does not modify the original job_table.csv or machine_table.csv files.
"""

from config.config import Config, config
from scheduler.data_loader import SchedulingDataLoader
from scheduler.fcfs import FCFSScheduler
from scheduler.optimizer import OrtoolsScheduler
from scheduler.kpi import KPICalculator
from scheduler.export import SchedulingExporter


def run_benchmark() -> None:
    """Generate dashboard-ready FCFS and optimizer results for the demo data."""
    Config.create_directories()
    loader = SchedulingDataLoader(config)
    jobs, _ = loader.load_jobs(Config.PROJECT_ROOT / "benchmark_job_table.csv")
    machines = loader.load_machines(Config.PROJECT_ROOT / "benchmark_machine_table.csv")
    rates = loader.load_energy_rates()

    fcfs_schedule = FCFSScheduler(config).solve(jobs, machines, rates)
    optimized_schedule = OrtoolsScheduler(config).solve(jobs, machines, rates)
    kpi_calculator = KPICalculator(config)
    SchedulingExporter(config).export_schedules_and_kpis(
        opt_df=optimized_schedule,
        fcfs_df=fcfs_schedule,
        opt_kpis=kpi_calculator.compute_kpis(optimized_schedule, machines, rates),
        fcfs_kpis=kpi_calculator.compute_kpis(fcfs_schedule, machines, rates),
        output_dir=Config.SCHEDULING_BENCHMARK_OUTPUT_DIR,
    )


if __name__ == "__main__":
    run_benchmark()
