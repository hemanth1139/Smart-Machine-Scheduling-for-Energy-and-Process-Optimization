"""
Scheduling Utilities Module.
Helper functions for discrete 15-minute time slot conversions, tariff calculations, and date parsing.
"""

from typing import Tuple, Union
import datetime
import math
import pandas as pd

from config.config import Config, config


def minutes_to_slots(minutes: float, slot_duration_min: int = Config.SLOT_DURATION_MIN) -> int:
    """Converts duration in minutes to integer count of 15-minute time slots (ceil rounded)."""
    return max(1, math.ceil(minutes / slot_duration_min))


def slot_to_time_str(slot: int, start_hour: int = 0, slot_duration_min: int = Config.SLOT_DURATION_MIN) -> str:
    """
    Converts time slot index to formatted HH:MM time string.

    Args:
        slot: Slot index (0-indexed).
        start_hour: Baseline hour for slot 0.
        slot_duration_min: Duration of each slot in minutes.

    Returns:
        str: Formatted time string (e.g. "08:30").
    """
    total_minutes = start_hour * 60 + slot * slot_duration_min
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"


def datetime_to_slot(dt: Union[pd.Timestamp, datetime.datetime, str], base_dt: Union[pd.Timestamp, datetime.datetime, None] = None, slot_duration_min: int = Config.SLOT_DURATION_MIN) -> int:
    """
    Converts datetime timestamp into relative time slot index from base_dt.

    Args:
        dt: Input timestamp.
        base_dt: Baseline start timestamp.
        slot_duration_min: Duration of each slot in minutes.

    Returns:
        int: Slot index (>= 0).
    """
    if isinstance(dt, str):
        dt = pd.to_datetime(dt)
    
    if base_dt is None:
        # Fall back to time-of-day slot
        total_mins = dt.hour * 60 + dt.minute
        return max(0, total_mins // slot_duration_min)

    if isinstance(base_dt, str):
        base_dt = pd.to_datetime(base_dt)

    diff_mins = (dt - base_dt).total_seconds() / 60.0
    return max(0, int(diff_mins // slot_duration_min))


def is_peak_slot(slot: int, slot_duration_min: int = Config.SLOT_DURATION_MIN, peak_hours: Tuple[int, int] = Config.PEAK_HOURS_RANGE) -> bool:
    """
    Determines if a given time slot index falls within peak tariff hours (e.g. 08:00 - 20:00).

    Args:
        slot: Slot index.
        slot_duration_min: Slot size in minutes.
        peak_hours: (start_hour, end_hour) tuple.

    Returns:
        bool: True if slot is within peak hours.
    """
    hour = ((slot * slot_duration_min) // 60) % 24
    return peak_hours[0] <= hour < peak_hours[1]


def calculate_slot_energy_rate(
    slot: int,
    forecasted_usage: float = 1.0,
    slot_duration_min: int = Config.SLOT_DURATION_MIN,
    peak_rate: float = Config.TARIFF_PEAK_RATE,
    offpeak_rate: float = Config.TARIFF_OFFPEAK_RATE,
) -> float:
    """
    Calculates effective energy cost rate ($/kWh * usage factor) for a time slot.

    Args:
        slot: Slot index.
        forecasted_usage: Predicted energy consumption multiplier (kWh).
        slot_duration_min: Duration in minutes.
        peak_rate: Peak electricity price ($/kWh).
        offpeak_rate: Off-peak electricity price ($/kWh).

    Returns:
        float: Cost rate for the slot.
    """
    tariff = peak_rate if is_peak_slot(slot, slot_duration_min) else offpeak_rate
    # 15 minutes is 0.25 hours
    hours_frac = slot_duration_min / 60.0
    return tariff * forecasted_usage * hours_frac
