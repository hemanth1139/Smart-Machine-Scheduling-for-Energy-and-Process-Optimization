"""
CP-SAT Constraint Formulator Module.
Formulates mathematical decision variables and OR-Tools CP-SAT constraints for machine scheduling.
"""

from typing import List, Dict, Tuple, Any
from ortools.sat.python import cp_model

from scheduler.data_loader import ParsedJob, ParsedMachine
from utils.logger import get_logger

logger = get_logger(__name__)


class ConstraintFormulator:
    """Class responsible for adding decision variables and physical scheduling constraints to CP-SAT model."""

    def __init__(self, model: cp_model.CpModel, horizon_slots: int):
        self.model = model
        self.horizon_slots = horizon_slots

        # Decision Variable Containers
        self.job_starts: Dict[str, cp_model.IntVar] = {}
        self.job_ends: Dict[str, cp_model.IntVar] = {}
        self.job_machines: Dict[Tuple[str, str], cp_model.BoolVar] = {}
        self.interval_vars: Dict[Tuple[str, str], cp_model.IntervalVar] = {}
        self.job_delays: Dict[str, cp_model.IntVar] = {}

    def create_variables_and_constraints(
        self, jobs: List[ParsedJob], machines: List[ParsedMachine]
    ) -> Dict[str, Any]:
        """
        Formulates all decision variables and CP-SAT physical constraints.

        Args:
            jobs: List of parsed job objects.
            machines: List of parsed machine objects.

        Returns:
            Dict[str, Any]: Dictionary containing created variable containers.
        """
        logger.info("Formulating CP-SAT decision variables and constraints...")

        machine_map = {m.machine_id: m for m in machines}
        machine_intervals: Dict[str, List[cp_model.IntervalVar]] = {m.machine_id: [] for m in machines}

        for j in jobs:
            # Global Start and End Variables for Job j
            start_var = self.model.NewIntVar(
                j.arrival_slot, self.horizon_slots, f"start_{j.job_id}"
            )
            end_var = self.model.NewIntVar(
                j.arrival_slot + j.duration_slots, self.horizon_slots + j.duration_slots, f"end_{j.job_id}"
            )
            delay_var = self.model.NewIntVar(0, self.horizon_slots, f"delay_{j.job_id}")

            self.job_starts[j.job_id] = start_var
            self.job_ends[j.job_id] = end_var
            self.job_delays[j.job_id] = delay_var

            # Constraint: End = Start + Duration
            self.model.Add(end_var == start_var + j.duration_slots)

            # Constraint: Delay = max(0, End - Deadline)
            self.model.Add(delay_var >= end_var - j.deadline_slot)
            self.model.Add(delay_var >= 0)

            # Compatibility & Machine Assignment Variables
            assigned_presence_vars = []
            for m_id in j.compatible_machines:
                if m_id not in machine_map:
                    continue

                m = machine_map[m_id]
                presence = self.model.NewBoolVar(f"x_{j.job_id}_{m_id}")
                self.job_machines[(j.job_id, m_id)] = presence
                assigned_presence_vars.append(presence)

                # Optional Interval for Job j on Machine m with Changeover Gap
                total_duration = j.duration_slots + m.changeover_slots
                
                interval = self.model.NewOptionalIntervalVar(
                    start_var,
                    total_duration,
                    start_var + total_duration,
                    presence,
                    f"interval_{j.job_id}_{m_id}",
                )
                self.interval_vars[(j.job_id, m_id)] = interval
                machine_intervals[m_id].append(interval)

                # Availability Constraint
                self.model.Add(start_var >= m.available_from_slot).OnlyEnforceIf(presence)
                self.model.Add(end_var <= m.available_to_slot).OnlyEnforceIf(presence)

            # Compatibility Constraint: Job must be assigned to EXACTLY ONE compatible machine
            if assigned_presence_vars:
                self.model.Add(sum(assigned_presence_vars) == 1)
            else:
                logger.warning(f"Job {j.job_id} has no valid compatible machines!")

        # Machine Non-Overlap Constraint (One job at a time per machine + changeover gap)
        for m_id, intervals in machine_intervals.items():
            if intervals:
                self.model.AddNoOverlap(intervals)

        logger.info("Decision variables and physical scheduling constraints successfully added.")

        return {
            "job_starts": self.job_starts,
            "job_ends": self.job_ends,
            "job_machines": self.job_machines,
            "job_delays": self.job_delays,
        }
