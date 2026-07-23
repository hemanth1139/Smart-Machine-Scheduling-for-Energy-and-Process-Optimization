"""
KPI Calculator Module.
Computes quantitative performance metrics (Energy Cost, Peak Load, Makespan, Utilization, Delays, On-Time %).
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from scheduler.data_loader import ParsedMachine
from scheduler.utils import is_peak_slot
from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class KPICalculator:
    """Computes comprehensive Key Performance Indicators (KPIs) for machine schedules."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def compute_kpis(
        self,
        schedule_df: pd.DataFrame,
        machines: List[ParsedMachine],
        energy_rates: List[float],
    ) -> Dict[str, Any]:
        """
        Computes all 10 scheduling Key Performance Indicators.

        Args:
            schedule_df: Schedule DataFrame containing Job_ID, Assigned_Machine, Start_Slot, End_Slot, etc.
            machines: List of parsed machine objects.
            energy_rates: List of energy cost rates per time slot.

        Returns:
            Dict[str, Any]: Dictionary of calculated KPIs.
        """
        if schedule_df.empty:
            logger.warning("Schedule DataFrame is empty. Returning default zero KPIs.")
            return {}

        machine_map = {m.machine_id: m for m in machines}
        horizon_slots = self.cfg.SCHEDULING_HORIZON_SLOTS
        slot_min = self.cfg.SLOT_DURATION_MIN

        total_jobs = len(schedule_df)

        # 1. Total Energy Cost ($)
        total_energy_cost = float(schedule_df["Energy_Cost_$"].sum())

        # 2. Peak-Hour Load (kWh)
        peak_load_kwh = 0.0
        for _, row in schedule_df.iterrows():
            m_obj = machine_map.get(row["Assigned_Machine"])
            if not m_obj:
                continue
            for t in range(int(row["Start_Slot"]), int(row["End_Slot"])):
                if is_peak_slot(t, slot_min):
                    peak_load_kwh += m_obj.active_power_kw * (slot_min / 60.0)

        # 3. Makespan (minutes & hours)
        makespan_slots = int(schedule_df["End_Slot"].max() - schedule_df["Start_Slot"].min())
        makespan_min = makespan_slots * slot_min
        makespan_hours = round(makespan_min / 60.0, 2)

        # 4. Machine Utilization & Total Idle Time
        num_machines = len(machines)
        total_available_slots = num_machines * horizon_slots

        total_active_slots = sum(row["End_Slot"] - row["Start_Slot"] for _, row in schedule_df.iterrows())
        overall_utilization_pct = round((total_active_slots / total_available_slots) * 100.0, 2)

        total_idle_slots = total_available_slots - total_active_slots
        total_idle_time_min = total_idle_slots * slot_min

        # 5. Waiting Time (Arrival to Start)
        waiting_times = [(row["Start_Slot"] - row["Arrival_Slot"]) * slot_min for _, row in schedule_df.iterrows()]
        avg_waiting_time_min = round(float(np.mean(waiting_times)), 2)

        # 6. Deadline Violations & Late Jobs
        late_jobs = int(schedule_df["Is_Late"].sum())
        on_time_jobs = total_jobs - late_jobs
        on_time_pct = round((on_time_jobs / total_jobs) * 100.0, 2)
        total_delay_min = float(schedule_df["Delay_min"].sum())

        # 7. Average Machine Load
        avg_machine_load_pct = round(overall_utilization_pct, 2)

        kpis = {
            "Total_Energy_Cost_$": round(total_energy_cost, 2),
            "Peak_Hour_Load_kWh": round(peak_load_kwh, 2),
            "Makespan_min": makespan_min,
            "Makespan_hours": makespan_hours,
            "Machine_Utilization_%": overall_utilization_pct,
            "Average_Waiting_Time_min": avg_waiting_time_min,
            "Total_Idle_Time_min": total_idle_time_min,
            "Total_Delay_min": round(total_delay_min, 2),
            "Number_of_Late_Jobs": late_jobs,
            "On_Time_Completion_%": on_time_pct,
            "Average_Machine_Load_%": avg_machine_load_pct,
        }

        logger.info("--------------------------------------------------")
        logger.info("SCHEDULE KEY PERFORMANCE INDICATORS (KPIs):")
        logger.info(f"  • Total Energy Cost:           ₹{kpis['Total_Energy_Cost_$']}")
        logger.info(f"  • Peak-Hour Load:              {kpis['Peak_Hour_Load_kWh']} kWh")
        logger.info(f"  • Makespan:                    {kpis['Makespan_hours']} hours ({kpis['Makespan_min']} min)")
        logger.info(f"  • Machine Utilization:         {kpis['Machine_Utilization_%']}%")
        logger.info(f"  • Average Waiting Time:        {kpis['Average_Waiting_Time_min']} min")
        logger.info(f"  • Late Jobs / Violations:      {kpis['Number_of_Late_Jobs']} jobs ({kpis['On_Time_Completion_%']}% On-Time)")
        logger.info("--------------------------------------------------")

        return kpis
