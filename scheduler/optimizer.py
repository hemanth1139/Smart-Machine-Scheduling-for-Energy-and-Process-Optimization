"""Baseline-safe energy-aware scheduling optimizer.

The optimiser begins with a feasible FCFS schedule and makes only Pareto-safe
changes. A move is accepted only when it lowers a job's energy cost without
increasing peak-hour load, lateness, or the FCFS makespan. This makes the
comparison table a fair energy-and-service benchmark rather than allowing
cheap energy savings to create late work.
"""

import time
from typing import Any, Dict, List, Tuple

import pandas as pd

from config.config import Config, config
from scheduler.base_scheduler import BaseScheduler
from scheduler.data_loader import ParsedJob, ParsedMachine
from scheduler.fcfs import FCFSScheduler
from scheduler.utils import extend_energy_rates, is_peak_slot, job_energy_cost, slot_to_time_str
from utils.logger import get_logger

logger = get_logger(__name__)


class OrtoolsScheduler(BaseScheduler):
    """Improve FCFS energy use while protecting all service-level KPIs.

    The class name is retained for compatibility with the existing pipeline.
    This implementation is a deterministic local search, not a CP-SAT model.
    """

    def __init__(self, cfg: Config = config):
        self.cfg = cfg
        self.solver_status = "FEASIBLE"
        self.solve_time_sec = 0.0

    def solve(
        self,
        jobs: List[Any],
        machines: List[Any],
        energy_rates: List[float],
    ) -> pd.DataFrame:
        t0 = time.time()
        if not jobs or not machines:
            return pd.DataFrame()

        parsed_jobs = jobs if isinstance(jobs[0], ParsedJob) else [ParsedJob(**job) for job in jobs]
        parsed_machines = machines if isinstance(machines[0], ParsedMachine) else [ParsedMachine(**machine) for machine in machines]
        machine_map = {machine.machine_id: machine for machine in parsed_machines}
        job_map = {job.job_id: job for job in parsed_jobs}
        slot_min = self.cfg.SLOT_DURATION_MIN

        # FCFS is always a feasible starting point. Each later move is bounded
        # by the FCFS makespan and the original deadline performance, so the
        # headline service KPIs cannot regress while work can move out of peak
        # tariff periods.
        fcfs_df = FCFSScheduler(self.cfg).solve(parsed_jobs, parsed_machines, energy_rates)
        if fcfs_df.empty:
            return fcfs_df

        max_slot = max(int(fcfs_df["End_Slot"].max()) + 1, self.cfg.SCHEDULING_HORIZON_SLOTS)
        rates = extend_energy_rates(list(energy_rates), max_slot + 1)

        placements: Dict[str, Dict[str, Any]] = {
            row["Job_ID"]: {
                "machine_id": row["Assigned_Machine"],
                "start": int(row["Start_Slot"]),
                "end": int(row["End_Slot"]),
            }
            for _, row in fcfs_df.iterrows()
        }
        fcfs_bounds = {job_id: placement.copy() for job_id, placement in placements.items()}
        fcfs_makespan_end = max(placement["end"] for placement in placements.values())
        intervals: Dict[str, List[Tuple[int, int, str]]] = {machine.machine_id: [] for machine in parsed_machines}
        for job_id, placement in placements.items():
            machine = machine_map[placement["machine_id"]]
            intervals[machine.machine_id].append(
                (placement["start"], placement["end"] + machine.changeover_slots, job_id)
            )

        total_peak = self._schedule_peak_load(placements, machine_map)
        improvements = 0

        # Process expensive jobs first; repeated passes let a released slot help
        # a subsequent job while every intermediate schedule remains feasible.
        for _ in range(2):
            changed = False
            order = sorted(
                placements,
                key=lambda job_id: self._energy_cost(placements[job_id], machine_map, job_map[job_id], rates),
                reverse=True,
            )
            for job_id in order:
                job = job_map[job_id]
                current = placements[job_id]
                current_machine = machine_map[current["machine_id"]]
                current_cost = self._energy_cost(current, machine_map, job, rates)
                current_peak = self._placement_peak_load(current, current_machine)

                intervals[current_machine.machine_id] = [
                    entry for entry in intervals[current_machine.machine_id] if entry[2] != job_id
                ]

                best = current
                best_cost = current_cost
                best_peak = current_peak
                baseline = fcfs_bounds[job_id]
                # Every FCFS on-time job must stay on time. A job that was
                # already late may only finish no later than its FCFS finish.
                latest_end = min(fcfs_makespan_end, job.deadline_slot)
                if baseline["end"] > job.deadline_slot:
                    latest_end = min(latest_end, baseline["end"])
                latest_start = latest_end - job.duration_slots
                for machine_id in job.compatible_machines:
                    machine = machine_map.get(machine_id)
                    if machine is None:
                        continue
                    for start in range(max(job.arrival_slot, machine.available_from_slot), latest_start + 1):
                        end = start + job.duration_slots
                        occupied_end = end + machine.changeover_slots
                        if end > latest_end or occupied_end > machine.available_to_slot:
                            continue
                        if self._overlaps(start, occupied_end, intervals[machine_id]):
                            continue
                        candidate = {"machine_id": machine_id, "start": start, "end": end}
                        candidate_cost = self._energy_cost(candidate, machine_map, job, rates)
                        candidate_peak = self._placement_peak_load(candidate, machine)
                        # Cost and peak load both have a minimisation direction.
                        if candidate_peak > current_peak + 1e-9:
                            continue
                        if candidate_cost < best_cost - 1e-9 or (
                            abs(candidate_cost - best_cost) <= 1e-9 and candidate_peak < best_peak - 1e-9
                        ):
                            best, best_cost, best_peak = candidate, candidate_cost, candidate_peak

                placements[job_id] = best
                best_machine = machine_map[best["machine_id"]]
                intervals[best_machine.machine_id].append(
                    (best["start"], best["end"] + best_machine.changeover_slots, job_id)
                )
                if best != current:
                    total_peak += best_peak - current_peak
                    improvements += 1
                    changed = True
            if not changed:
                break

        records = []
        for job_id, placement in placements.items():
            job = job_map[job_id]
            machine = machine_map[placement["machine_id"]]
            end = placement["end"]
            delay_slots = max(0, end - job.deadline_slot)
            records.append({
                "Job_ID": job_id,
                "Assigned_Machine": machine.machine_id,
                "Machine_Type": machine.machine_type,
                "Start_Slot": placement["start"],
                "End_Slot": end,
                "Start_Time": slot_to_time_str(placement["start"]),
                "End_Time": slot_to_time_str(end),
                "Duration_min": job.duration_min,
                "Arrival_Slot": job.arrival_slot,
                "Deadline_Slot": job.deadline_slot,
                "Delay_min": delay_slots * slot_min,
                "Is_Late": int(delay_slots > 0),
                "Energy_Cost_$": round(self._energy_cost(placement, machine_map, job, rates), 2),
                "Priority": job.priority,
            })

        result = pd.DataFrame(records).sort_values("Start_Slot").reset_index(drop=True)
        self.solve_time_sec = round(time.time() - t0, 2)
        logger.info("Baseline-safe optimizer complete in %ss; accepted %s safe improvements.", self.solve_time_sec, improvements)
        return result

    def _energy_cost(self, placement: Dict[str, Any], machine_map: Dict[str, ParsedMachine], job: ParsedJob, rates: List[float]) -> float:
        machine = machine_map[placement["machine_id"]]
        kwh_per_slot = machine.active_power_kw * (self.cfg.SLOT_DURATION_MIN / 60.0)
        return job_energy_cost(placement["start"], job.duration_slots, kwh_per_slot, rates)

    def _placement_peak_load(self, placement: Dict[str, Any], machine: ParsedMachine) -> float:
        kwh_per_slot = machine.active_power_kw * (self.cfg.SLOT_DURATION_MIN / 60.0)
        return sum(
            kwh_per_slot
            for slot in range(placement["start"], placement["end"])
            if is_peak_slot(slot, self.cfg.SLOT_DURATION_MIN)
        )

    def _schedule_peak_load(self, placements: Dict[str, Dict[str, Any]], machine_map: Dict[str, ParsedMachine]) -> float:
        return sum(self._placement_peak_load(placement, machine_map[placement["machine_id"]]) for placement in placements.values())

    @staticmethod
    def _overlaps(start: int, end: int, intervals: List[Tuple[int, int, str]]) -> bool:
        return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end, _ in intervals)
