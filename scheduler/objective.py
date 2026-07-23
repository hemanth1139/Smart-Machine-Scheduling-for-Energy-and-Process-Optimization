"""
CP-SAT Objective Function Formulator.
Constructs multi-objective cost minimization function combining time-slot-specific energy cost,
deadline penalties, changeovers, and makespan.
"""

from typing import List, Dict, Tuple, Any
from ortools.sat.python import cp_model

from config.config import Config, config
from scheduler.data_loader import ParsedJob, ParsedMachine
from utils.logger import get_logger

logger = get_logger(__name__)


class ObjectiveFormulator:
    """Class responsible for building multi-objective cost function in CP-SAT model."""

    def __init__(self, model: cp_model.CpModel, cfg: Config = config):
        self.model = model
        self.cfg = cfg

    def add_objective_function(
        self,
        jobs: List[ParsedJob],
        machines: List[ParsedMachine],
        energy_rates: List[float],
        var_containers: Dict[str, Any],
    ) -> cp_model.IntVar:
        """
        Formulates and attaches multi-objective minimization cost expression to the CP-SAT model.

        Args:
            jobs: Parsed jobs.
            machines: Parsed machines.
            energy_rates: Cost rate per time slot.
            var_containers: Variable containers output by ConstraintFormulator.

        Returns:
            cp_model.IntVar: Objective total cost variable.
        """
        logger.info("Formulating multi-objective cost minimization function...")

        job_starts = var_containers["job_starts"]
        job_ends = var_containers["job_ends"]
        job_machines = var_containers["job_machines"]
        job_delays = var_containers["job_delays"]

        horizon = self.cfg.SCHEDULING_HORIZON_SLOTS
        slot_hours = self.cfg.SLOT_DURATION_MIN / 60.0

        # 1. Makespan Variable: max(end_j) across all jobs
        makespan_var = self.model.NewIntVar(0, horizon + 200, "makespan")
        for j in jobs:
            self.model.Add(makespan_var >= job_ends[j.job_id])

        # 2. Weighted Deadline Delay Penalties
        deadline_penalty_terms = []
        for j in jobs:
            delay_var = job_delays[j.job_id]
            # Multiply delay by job priority weight and configured penalty weight
            weighted_delay = delay_var * int(j.priority_weight * self.cfg.WEIGHT_DEADLINE_PENALTY * 100)
            deadline_penalty_terms.append(weighted_delay)

        # 3. Dynamic Time-Slot Energy Cost Optimization
        # For each job j on machine m, energy cost depends on exact start slot s
        energy_cost_terms = []
        machine_map = {m.machine_id: m for m in machines}

        for j in jobs:
            start_var = job_starts[j.job_id]

            for m_id in j.compatible_machines:
                if (j.job_id, m_id) not in job_machines:
                    continue

                presence = job_machines[(j.job_id, m_id)]
                m = machine_map[m_id]

                # Precompute energy cost integer for each possible start slot s in [0..horizon]
                cost_array = []
                for s in range(horizon + 1):
                    job_kwh_cost = 0.0
                    for t in range(s, min(s + j.duration_slots, len(energy_rates))):
                        rate = energy_rates[t] if t < len(energy_rates) else (energy_rates[-1] if energy_rates else 0.15)
                        kwh = m.active_power_kw * slot_hours
                        job_kwh_cost += kwh * rate

                    # Scale to integer (x 100) for CP-SAT solver precision
                    cost_int = int(round(job_kwh_cost * 100 * self.cfg.WEIGHT_ENERGY_COST))
                    cost_array.append(cost_int)

                # CP-SAT Element constraint: cost_for_slot = cost_array[start_var]
                max_cost_val = max(cost_array) if cost_array else 10000
                cost_for_slot = self.model.NewIntVar(0, max_cost_val, f"slot_cost_{j.job_id}_{m_id}")
                self.model.AddElement(start_var, cost_array, cost_for_slot)

                # Active energy cost variable enforced only if job is assigned to this machine
                active_cost = self.model.NewIntVar(0, max_cost_val, f"active_cost_{j.job_id}_{m_id}")
                self.model.Add(active_cost == cost_for_slot).OnlyEnforceIf(presence)
                self.model.Add(active_cost == 0).OnlyEnforceIf(presence.Not())

                energy_cost_terms.append(active_cost)

        # Combine all objective terms into single total cost expression
        total_objective = (
            sum(energy_cost_terms)
            + sum(deadline_penalty_terms)
            + (makespan_var * int(self.cfg.WEIGHT_MAKESPAN * 10))
        )

        self.model.Minimize(total_objective)
        logger.info("Multi-objective time-slot energy cost function successfully formulated.")
        return makespan_var
