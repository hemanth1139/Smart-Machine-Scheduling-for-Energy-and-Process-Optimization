"""
OR-Tools CP-SAT Machine Scheduler Engine.
Solves the exact multi-objective machine job scheduling problem minimizing energy cost, delays, and makespan.
Uses FCFS baseline warm-starting (AddHint) to guarantee feasibility and rapid convergence to optimal energy savings.
"""

from typing import List, Dict, Any, Tuple
from ortools.sat.python import cp_model
import pandas as pd
import numpy as np

from scheduler.base_scheduler import BaseScheduler
from scheduler.data_loader import ParsedJob, ParsedMachine
from scheduler.constraints import ConstraintFormulator
from scheduler.objective import ObjectiveFormulator
from scheduler.fcfs import FCFSScheduler
from scheduler.utils import slot_to_time_str
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class OrtoolsScheduler(BaseScheduler):
    """Google OR-Tools CP-SAT Optimization Solver Implementation."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg
        self.solver_status: str = "UNKNOWN"
        self.solve_time_sec: float = 0.0

    def solve(
        self,
        jobs: List[Dict[str, Any]],
        machines: List[Dict[str, Any]],
        energy_rates: List[float],
    ) -> pd.DataFrame:
        """
        Executes Google OR-Tools CP-SAT optimization with FCFS warm-starting.

        Args:
            jobs: List of ParsedJob or job dicts.
            machines: List of ParsedMachine or machine dicts.
            energy_rates: Energy cost rates per time slot.

        Returns:
            pd.DataFrame: CP-SAT optimized schedule DataFrame.
        """
        logger.info("==================================================")
        logger.info("Starting Google OR-Tools CP-SAT Optimization Engine")
        logger.info("==================================================")

        parsed_jobs = jobs if isinstance(jobs[0], ParsedJob) else [ParsedJob(**j) for j in jobs]
        parsed_machines = machines if isinstance(machines[0], ParsedMachine) else [ParsedMachine(**m) for m in machines]

        machine_map = {m.machine_id: m for m in parsed_machines}

        # 1. Run FCFS Baseline to generate feasible warm-start hint
        logger.info("Generating FCFS baseline warm-start hints for CP-SAT solver...")
        fcfs_scheduler = FCFSScheduler(self.cfg)
        fcfs_df = fcfs_scheduler.solve(parsed_jobs, parsed_machines, energy_rates)
        fcfs_map = {row["Job_ID"]: row for _, row in fcfs_df.iterrows()}

        # Determine horizon dynamically from max job end slot
        max_fcfs_end = int(fcfs_df["End_Slot"].max()) if not fcfs_df.empty else self.cfg.SCHEDULING_HORIZON_SLOTS
        horizon_slots = max(self.cfg.SCHEDULING_HORIZON_SLOTS, max_fcfs_end + 10)

        # Extend energy_rates to match full horizon if needed
        rates = list(energy_rates)
        if len(rates) < horizon_slots:
            rates.extend([rates[-1] if rates else 0.15] * (horizon_slots - len(rates)))

        # 2. Instantiate CP-SAT Model
        model = cp_model.CpModel()

        # 3. Formulate Decision Variables & Physical Constraints
        constraint_builder = ConstraintFormulator(model=model, horizon_slots=horizon_slots)
        var_containers = constraint_builder.create_variables_and_constraints(
            jobs=parsed_jobs, machines=parsed_machines
        )

        job_starts = var_containers["job_starts"]
        job_ends = var_containers["job_ends"]
        job_machines = var_containers["job_machines"]

        # 4. Apply Warm Start Hints from FCFS Baseline
        for j in parsed_jobs:
            if j.job_id in fcfs_map:
                fcfs_row = fcfs_map[j.job_id]
                start_slot = int(fcfs_row["Start_Slot"])
                assigned_m = str(fcfs_row["Assigned_Machine"])

                model.AddHint(job_starts[j.job_id], start_slot)
                if (j.job_id, assigned_m) in job_machines:
                    model.AddHint(job_machines[(j.job_id, assigned_m)], 1)

        # 5. Formulate Multi-Objective Function (Dynamic Tariff Energy Cost + Delays + Makespan)
        obj_builder = ObjectiveFormulator(model=model, cfg=self.cfg)
        obj_builder.add_objective_function(
            jobs=parsed_jobs,
            machines=parsed_machines,
            energy_rates=rates,
            var_containers=var_containers,
        )

        # 6. Configure CP-SAT Solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.cfg.ORTOOLS_TIME_LIMIT_SEC
        solver.parameters.num_search_workers = 4
        solver.parameters.log_search_progress = False

        logger.info(f"Solving CP-SAT model (horizon={horizon_slots} slots, time_limit={self.cfg.ORTOOLS_TIME_LIMIT_SEC}s)...")
        status = solver.Solve(model)

        self.solver_status = solver.StatusName(status)
        self.solve_time_sec = round(solver.WallTime(), 2)

        logger.info(f"CP-SAT Solver Finished. Status: '{self.solver_status}', Wall Time: {self.solve_time_sec}s")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.warning("CP-SAT Solver failed to improve hint. Returning FCFS baseline schedule.")
            return fcfs_df

        # 7. Extract CP-SAT Optimized Solution Records
        job_delays = var_containers["job_delays"]
        optimized_records = []

        for j in parsed_jobs:
            start_val = int(solver.Value(job_starts[j.job_id]))
            end_val = int(solver.Value(job_ends[j.job_id]))
            delay_val = int(solver.Value(job_delays[j.job_id]))

            assigned_m_id = j.compatible_machines[0] if j.compatible_machines else "M1"
            for m_id in j.compatible_machines:
                if (j.job_id, m_id) in job_machines and solver.Value(job_machines[(j.job_id, m_id)]) == 1:
                    assigned_m_id = m_id
                    break

            m_obj = machine_map[assigned_m_id]

            # Calculate Exact Energy Cost for Optimized Start/End Window
            job_energy_cost = 0.0
            for t in range(start_val, min(end_val, len(rates))):
                rate = rates[t] if t < len(rates) else rates[-1]
                kwh = m_obj.active_power_kw * (self.cfg.SLOT_DURATION_MIN / 60.0)
                job_energy_cost += kwh * rate

            delay_min = delay_val * self.cfg.SLOT_DURATION_MIN

            optimized_records.append({
                "Job_ID": j.job_id,
                "Assigned_Machine": assigned_m_id,
                "Machine_Type": m_obj.machine_type,
                "Start_Slot": start_val,
                "End_Slot": end_val,
                "Start_Time": slot_to_time_str(start_val),
                "End_Time": slot_to_time_str(end_val),
                "Duration_min": j.duration_min,
                "Arrival_Slot": j.arrival_slot,
                "Deadline_Slot": j.deadline_slot,
                "Delay_min": delay_min,
                "Is_Late": 1 if delay_min > 0 else 0,
                "Energy_Cost_$": round(job_energy_cost, 2),
                "Priority": j.priority,
            })

        opt_df = pd.DataFrame(optimized_records).sort_values(by="Start_Slot").reset_index(drop=True)
        logger.info(f"CP-SAT Optimization complete. Successfully scheduled {len(opt_df)} jobs.")
        return opt_df
