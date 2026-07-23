"""
First-Come-First-Served (FCFS) Baseline Scheduler Module.
Implements a greedy FCFS dispatching heuristic for benchmark comparison against CP-SAT optimization.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from scheduler.base_scheduler import BaseScheduler
from scheduler.data_loader import ParsedJob, ParsedMachine
from scheduler.utils import slot_to_time_str, is_peak_slot
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class FCFSScheduler(BaseScheduler):
    """First-Come-First-Served baseline scheduling engine."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def solve(
        self,
        jobs: List[Dict[str, Any]],
        machines: List[Dict[str, Any]],
        energy_rates: List[float],
    ) -> pd.DataFrame:
        """
        Executes FCFS scheduling heuristic.

        Args:
            jobs: List of job specification dicts or ParsedJob objects.
            machines: List of machine specification dicts or ParsedMachine objects.
            energy_rates: List of energy cost rates per time slot.

        Returns:
            pd.DataFrame: FCFS baseline schedule dataframe.
        """
        logger.info("Executing baseline First-Come-First-Served (FCFS) Scheduler...")

        # Parse inputs if raw dicts passed
        parsed_jobs = jobs if isinstance(jobs[0], ParsedJob) else [ParsedJob(**j) for j in jobs]
        parsed_machines = machines if isinstance(machines[0], ParsedMachine) else [ParsedMachine(**m) for m in machines]

        machine_map = {m.machine_id: m for m in parsed_machines}
        
        # Track when each machine becomes free (slot index)
        machine_next_available: Dict[str, int] = {m.machine_id: m.available_from_slot for m in parsed_machines}

        # Sort jobs by Arrival Slot, then Priority Weight (descending)
        sorted_jobs = sorted(parsed_jobs, key=lambda j: (j.arrival_slot, -j.priority_weight))

        scheduled_records = []

        for j in sorted_jobs:
            # Filter compatible machines
            valid_machines = [m_id for m_id in j.compatible_machines if m_id in machine_map]
            if not valid_machines:
                logger.warning(f"FCFS: Job {j.job_id} has no compatible machines.")
                continue

            # Find compatible machine available earliest at or after job arrival
            best_m_id = None
            best_start_slot = float("inf")

            for m_id in valid_machines:
                earliest = max(j.arrival_slot, machine_next_available[m_id])
                if earliest < best_start_slot:
                    best_start_slot = earliest
                    best_m_id = m_id

            m_obj = machine_map[best_m_id]
            start_slot = int(best_start_slot)
            end_slot = start_slot + j.duration_slots

            # Update machine availability including changeover gap
            machine_next_available[best_m_id] = end_slot + m_obj.changeover_slots

            # Calculate Delay
            delay_slots = max(0, end_slot - j.deadline_slot)
            delay_min = delay_slots * self.cfg.SLOT_DURATION_MIN

            # Compute Energy Cost
            job_energy_cost = 0.0
            for t in range(start_slot, min(end_slot, len(energy_rates))):
                rate = energy_rates[t] if t < len(energy_rates) else energy_rates[-1]
                # kWh consumed in slot = ActivePower * (15/60)
                kwh = m_obj.active_power_kw * (self.cfg.SLOT_DURATION_MIN / 60.0)
                job_energy_cost += kwh * rate

            scheduled_records.append({
                "Job_ID": j.job_id,
                "Assigned_Machine": best_m_id,
                "Machine_Type": m_obj.machine_type,
                "Start_Slot": start_slot,
                "End_Slot": end_slot,
                "Start_Time": slot_to_time_str(start_slot),
                "End_Time": slot_to_time_str(end_slot),
                "Duration_min": j.duration_min,
                "Arrival_Slot": j.arrival_slot,
                "Deadline_Slot": j.deadline_slot,
                "Delay_min": delay_min,
                "Is_Late": 1 if delay_min > 0 else 0,
                "Energy_Cost_$": round(job_energy_cost, 2),
                "Priority": j.priority,
            })

        fcfs_df = pd.DataFrame(scheduled_records).sort_values(by="Start_Slot").reset_index(drop=True)
        logger.info(f"FCFS baseline scheduling complete. Scheduled {len(fcfs_df)} jobs.")
        return fcfs_df
