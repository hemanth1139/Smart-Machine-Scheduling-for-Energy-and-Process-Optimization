"""
Scheduling Data Loader Module.
Loads cleaned Job, Machine, and Phase 2 predicted energy demand datasets.
Parses attributes into structured data representations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from config.config import Config, config
from scheduler.utils import minutes_to_slots, datetime_to_slot, calculate_slot_energy_rate
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedJob:
    """Dataclass representing a parsed production job."""
    job_id: str
    duration_min: float
    duration_slots: int
    arrival_slot: int
    deadline_slot: int
    priority: str
    priority_weight: int
    compatible_machines: List[str]
    arrival_time_str: str
    deadline_str: str


@dataclass
class ParsedMachine:
    """Dataclass representing a parsed machine resource."""
    machine_id: str
    machine_type: str
    idle_power_kw: float
    active_power_kw: float
    changeover_min: float
    changeover_slots: int
    available_from_slot: int
    available_to_slot: int


class SchedulingDataLoader:
    """Loader and parser for scheduling input datasets."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def load_jobs(self, file_path: Optional[Path] = None) -> Tuple[List[ParsedJob], pd.Timestamp]:
        """
        Loads and parses jobs dataset into structured ParsedJob objects.

        Returns:
            Tuple[List[ParsedJob], pd.Timestamp]: List of parsed jobs and baseline start timestamp.
        """
        if file_path is None:
            file_path = self.cfg.PROCESSED_DATA_DIR / self.cfg.JOB_CLEANED_FILENAME
            if not file_path.exists():
                file_path = self.cfg.get_raw_path(self.cfg.JOB_DATA_FILENAME)

        logger.info(f"Loading Job dataset for scheduling from: {file_path}")
        df = pd.read_csv(file_path)

        arr_col = "Arrival_Time" if "Arrival_Time" in df.columns else df.columns[-1]
        base_ts = pd.to_datetime(df[arr_col]).min().floor("D")

        priority_map = {"High": 3, "Medium": 2, "Low": 1}

        parsed_jobs = []
        for idx, row in df.iterrows():
            job_id = str(row.get("Job_ID", f"J{idx+1}"))
            dur_min = float(row.get("Duration_min", 60))
            dur_slots = minutes_to_slots(dur_min, self.cfg.SLOT_DURATION_MIN)

            arr_str = str(row.get("Arrival_Time", "2026-01-01 00:00"))
            dl_str = str(row.get("Deadline", "2026-01-01 23:59"))

            arr_slot = datetime_to_slot(arr_str, base_ts, self.cfg.SLOT_DURATION_MIN)
            dl_slot = datetime_to_slot(dl_str, base_ts, self.cfg.SLOT_DURATION_MIN)

            if dl_slot <= arr_slot + dur_slots:
                dl_slot = arr_slot + dur_slots + 4

            prio = str(row.get("Priority", "Medium"))
            prio_wt = priority_map.get(prio, 2)

            comp_str = str(row.get("Compatible_Machines", "M1,M2,M3"))
            comp_machines = [m.strip() for m in comp_str.split(",") if m.strip()]

            parsed_jobs.append(
                ParsedJob(
                    job_id=job_id,
                    duration_min=dur_min,
                    duration_slots=dur_slots,
                    arrival_slot=arr_slot,
                    deadline_slot=dl_slot,
                    priority=prio,
                    priority_weight=prio_wt,
                    compatible_machines=comp_machines,
                    arrival_time_str=arr_str,
                    deadline_str=dl_str,
                )
            )

        logger.info(f"Successfully parsed {len(parsed_jobs)} jobs. Baseline Timestamp: {base_ts}")
        return parsed_jobs, base_ts

    def load_machines(self, file_path: Optional[Path] = None) -> List[ParsedMachine]:
        """
        Loads and parses machine dataset into structured ParsedMachine objects.

        Returns:
            List[ParsedMachine]: List of parsed machines.
        """
        if file_path is None:
            file_path = self.cfg.PROCESSED_DATA_DIR / self.cfg.MACHINE_CLEANED_FILENAME
            if not file_path.exists():
                file_path = self.cfg.get_raw_path(self.cfg.MACHINE_DATA_FILENAME)

        logger.info(f"Loading Machine dataset for scheduling from: {file_path}")
        df = pd.read_csv(file_path)

        parsed_machines = []
        for idx, row in df.iterrows():
            m_id = str(row.get("Machine_ID", f"M{idx+1}"))
            m_type = str(row.get("Machine_Type", "General"))
            idle_p = float(row.get("Idle_Power_kW", 2.0))
            active_p = float(row.get("Active_Power_kW", 15.0))

            chg_min = float(row.get("Changeover_Time_min", 15))
            chg_slots = minutes_to_slots(chg_min, self.cfg.SLOT_DURATION_MIN)

            from_slot = 0
            to_slot = 10000  # unconstrained upper bound for 23:59 machine availability

            parsed_machines.append(
                ParsedMachine(
                    machine_id=m_id,
                    machine_type=m_type,
                    idle_power_kw=idle_p,
                    active_power_kw=active_p,
                    changeover_min=chg_min,
                    changeover_slots=chg_slots,
                    available_from_slot=from_slot,
                    available_to_slot=to_slot,
                )
            )

        logger.info(f"Successfully parsed {len(parsed_machines)} machines.")
        return parsed_machines

    def load_energy_rates(self, forecast_path: Optional[Path] = None) -> List[float]:
        """
        Loads predicted energy demand/cost profile per 15-minute time slot from Phase 2.

        Returns:
            List[float]: Electricity cost rate ($/kWh * usage multiplier) for each slot.
        """
        horizon_slots = self.cfg.SCHEDULING_HORIZON_SLOTS

        if forecast_path is None:
            forecast_path = self.cfg.FUTURE_FORECAST_CSV_PATH
            if not forecast_path.exists():
                forecast_path = self.cfg.PREDICTIONS_CSV_PATH

        if forecast_path.exists():
            logger.info(f"Loading Phase 2 energy demand predictions from: {forecast_path}")
            df = pd.read_csv(forecast_path)
            col = "predicted_kWh" if "predicted_kWh" in df.columns else df.columns[-1]
            predicted_usage = df[col].values[:horizon_slots]
        else:
            logger.warning("Phase 2 forecast file not found. Using baseline synthetic energy load profile.")
            predicted_usage = np.ones(horizon_slots)

        if len(predicted_usage) < horizon_slots:
            pad = np.tile(predicted_usage, int(np.ceil(horizon_slots / len(predicted_usage))))[:horizon_slots]
            predicted_usage = pad
        else:
            predicted_usage = predicted_usage[:horizon_slots]

        rates = [
            calculate_slot_energy_rate(
                slot=t,
                forecasted_usage=float(predicted_usage[t]),
                slot_duration_min=self.cfg.SLOT_DURATION_MIN,
                peak_rate=self.cfg.TARIFF_PEAK_RATE,
                offpeak_rate=self.cfg.TARIFF_OFFPEAK_RATE,
            )
            for t in range(horizon_slots)
        ]

        logger.info(f"Constructed energy cost rate profile for {horizon_slots} time slots.")
        return rates
