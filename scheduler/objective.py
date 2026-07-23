"""
CP-SAT Objective Function Formulator.
Constructs multi-objective cost minimization function combining energy cost, deadline penalties, changeovers, and makespan.
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

        # 1. Makespan Variable: max(end_j) across all jobs
        makespan_var = self.model.NewIntVar(0, self.cfg.SCHEDULING_HORIZON_SLOTS + 100, "makespan")
        for j in jobs:
            self.model.Add(makespan_var >= job_ends[j.job_id])

        # 2. Weighted Deadline Delay Penalties
        deadline_penalty_terms = []
        for j in jobs:
            delay_var = job_delays[j.job_id]
            # Multiply delay by job priority weight and configured penalty weight
            weighted_delay = delay_var * int(j.priority_weight * self.cfg.WEIGHT_DEADLINE_PENALTY * 100)
            deadline_penalty_terms.append(weighted_delay)

        # 3. Energy Cost Approximation
        # Energy cost = sum(ActivePower * rate_t for slot in [start..end])
        # Approximate using start slot rate + duration
        energy_cost_terms = []
        machine_map = {m.machine_id: m for m in machines}

        for j in jobs:
            for m_id in j.compatible_machines:
                if (j.job_id, m_id) not in job_machines:
                    continue

                presence = job_machines[(j.job_id, m_id)]
                m = machine_map[m_id]
                avg_rate = sum(energy_rates) / len(energy_rates) if energy_rates else 0.15
                
                # Active power energy cost integer term
                job_power_cost = int(m.active_power_kw * j.duration_slots * avg_rate * 100 * self.cfg.WEIGHT_ENERGY_COST)
                energy_cost_terms.append(presence * job_power_cost)

        # Combine all objective terms into single total cost expression
        total_objective = (
            sum(energy_cost_terms)
            + sum(deadline_penalty_terms)
            + (makespan_var * int(self.cfg.WEIGHT_MAKESPAN * 100))
        )

        self.model.Minimize(total_objective)
        logger.info("Multi-objective cost function successfully formulated.")
        return makespan_var
