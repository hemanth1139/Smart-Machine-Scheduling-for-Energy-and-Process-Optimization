"""
Abstract Base Class for Machine Scheduling Engines.
Establishes a uniform interface for optimization algorithms (OR-Tools, FCFS, Genetic Algorithms, RL).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
import pandas as pd


class BaseScheduler(ABC):
    """Abstract Base Interface for Machine Scheduling Solvers."""

    @abstractmethod
    def solve(
        self,
        jobs: List[Dict[str, Any]],
        machines: List[Dict[str, Any]],
        energy_rates: List[float],
    ) -> pd.DataFrame:
        """
        Executes scheduling optimization for given jobs, machines, and energy price profile.

        Args:
            jobs: List of job specification dictionaries.
            machines: List of machine specification dictionaries.
            energy_rates: List of energy cost rates ($/kWh or predicted Usage) per time slot.

        Returns:
            pd.DataFrame: DataFrame containing assigned schedule details (Job_ID, Machine_ID, Start_Slot, End_Slot, etc.).
        """
        pass
