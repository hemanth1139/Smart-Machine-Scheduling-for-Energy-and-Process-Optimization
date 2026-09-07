"""
KPI Calculation Engine.
Computes comprehensive operational, economic, and environmental metrics.

Fair accounting rules (critical for publication benchmarks):
  - Energy / CO2 are charged for EVERY scheduled job slot, not only those
    inside the 48h forecast window (cyclic tariff / CO2 extension).
  - Idle power is charged over the schedule makespan (not a truncated horizon),
    so deferring work outside the forecast cannot artificially zero out cost.
  - Utilization is relative to makespan × fleet size.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
try:
    from backend.config import config
except ImportError:
    from config import config


def _cyclic_series(forecast_df: pd.DataFrame, length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build tariff / CO2 / PF arrays of `length`, repeating the forecast pattern."""
    base_n = max(1, len(forecast_df))
    tariffs = np.zeros(length)
    co2 = np.zeros(length)
    pf = np.zeros(length)

    for t in range(length):
        row = forecast_df.iloc[t % base_n]
        load_type = row.get("Load_Type", "Light_Load")
        if load_type == "Maximum_Load":
            tariffs[t] = config.TARIFF_MAX_LOAD
        elif load_type == "Medium_Load":
            tariffs[t] = config.TARIFF_MED_LOAD
        else:
            tariffs[t] = config.TARIFF_LIGHT_LOAD
        co2[t] = float(row.get("predicted_CO2_p50", 0.05) or 0.05)
        pf[t] = float(row.get("predicted_PF_p50", 0.92) or 0.92)

    return tariffs, co2, pf


def compute_schedule_kpis(
    schedule_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Computes KPIs dynamically for a given schedule."""
    if schedule_df.empty:
        return {
            "Total_Energy_Cost_INR": 0.0,
            "Peak_Hour_Load_kW": 0.0,
            "Makespan_min": 0.0,
            "Makespan_hours": 0.0,
            "Machine_Utilization_pct": 0.0,
            "Average_Waiting_Time_min": 0.0,
            "Total_Idle_Time_min": 0.0,
            "Total_Delay_min": 0.0,
            "Late_Jobs": 0,
            "On_Time_Completion_pct": 100.0,
            "Total_Carbon_Emissions_tCO2": 0.0,
            "Total_Power_Factor_Penalty_INR": 0.0,
        }

    job_map = jobs_df.set_index("Job_ID").to_dict(orient="index")
    mach_map = machines_df.set_index("Machine_ID").to_dict(orient="index")
    mids = list(mach_map.keys())

    max_end = int(schedule_df["End_Slot"].max())
    min_start = int(schedule_df["Start_Slot"].min())
    # Evaluate at least the planning horizon; extend if schedule runs longer
    eval_slots = max(config.SCHEDULING_HORIZON_SLOTS, max_end, 1)

    tariffs, co2_rates, pf_values = _cyclic_series(forecast_df, eval_slots)

    # Per-slot active machine power (kW)
    active_power_slots = np.zeros(eval_slots)
    machine_busy = {mid: np.zeros(eval_slots, dtype=np.int8) for mid in mids}

    total_delay = 0.0
    late_jobs_count = 0
    total_waiting_time = 0.0
    total_energy_cost = 0.0
    total_carbon = 0.0
    hours_per_slot = config.SLOT_DURATION_MIN / 60.0

    for _, row in schedule_df.iterrows():
        jid = row["Job_ID"]
        mid = row["Machine_ID"]
        start_slot = int(row["Start_Slot"])
        end_slot = int(row["End_Slot"])
        j_p = job_map[jid]
        m_p = mach_map[mid]
        active_kw = float(m_p["Active_Power_kW"])
        setup_kw = float(m_p.get("Setup_Energy_kW", 0.0))

        # Job-centric active energy (never truncated)
        for t in range(start_slot, end_slot):
            t_idx = min(t, eval_slots - 1)
            e_kwh = active_kw * hours_per_slot
            total_energy_cost += e_kwh * tariffs[t_idx]
            total_carbon += e_kwh * co2_rates[t_idx]
            if 0 <= t < eval_slots:
                active_power_slots[t] += active_kw
                machine_busy[mid][t] = 1

        # Setup energy at start
        s_idx = min(max(start_slot, 0), eval_slots - 1)
        setup_kwh = setup_kw * hours_per_slot
        total_energy_cost += setup_kwh * tariffs[s_idx]
        total_carbon += setup_kwh * co2_rates[s_idx]

        deadline_slot = int(j_p["Deadline"])
        if end_slot > deadline_slot:
            total_delay += (end_slot - deadline_slot) * config.SLOT_DURATION_MIN
            late_jobs_count += 1

        arrival_slot = int(j_p["Arrival_Time"])
        total_waiting_time += max(0, start_slot - arrival_slot) * config.SLOT_DURATION_MIN

    # Idle power over makespan window [min_start, max_end)
    makespan_slots = max(1, max_end - min_start)
    idle_cost = 0.0
    idle_carbon = 0.0
    total_pf_penalty = 0.0
    total_active_slots = 0.0

    for t in range(min_start, max_end):
        t_idx = min(t, eval_slots - 1)
        slot_idle_kw = 0.0
        for mid, m_p in mach_map.items():
            if t < eval_slots and machine_busy[mid][t] == 1:
                total_active_slots += 1.0
            else:
                slot_idle_kw += float(m_p["Idle_Power_kW"])

        idle_kwh = slot_idle_kw * hours_per_slot
        idle_cost += idle_kwh * tariffs[t_idx]
        idle_carbon += idle_kwh * co2_rates[t_idx]

        pf_t = pf_values[t_idx]
        if pf_t < 0.90:
            # Approximate PF surcharge on total slot draw
            slot_active = active_power_slots[t_idx] if t_idx < len(active_power_slots) else 0.0
            total_pf_penalty += (slot_active + slot_idle_kw) * hours_per_slot * tariffs[t_idx] * (0.90 - pf_t) * 2.0

    total_energy_cost += idle_cost
    total_carbon += idle_carbon

    # Peak plant load during Maximum_Load (billing) hours — industrial demand-charge proxy.
    # Overall night peaks after intentional off-peak shifting are not billed the same way.
    max_load_mask = tariffs >= config.TARIFF_MAX_LOAD - 1e-6
    if max_load_mask.any():
        peak_machine_load = float(active_power_slots[max_load_mask].max())
    else:
        peak_machine_load = float(active_power_slots.max()) if len(active_power_slots) else 0.0

    baseline = 0.0
    if "predicted_kWh_p50" in forecast_df.columns and len(forecast_df):
        # Use peak-hour baseline only
        peak_rows = forecast_df[forecast_df.get("Load_Type", "") == "Maximum_Load"] if "Load_Type" in forecast_df.columns else forecast_df
        if len(peak_rows):
            baseline = float(peak_rows["predicted_kWh_p50"].max())
        else:
            baseline = float(forecast_df["predicted_kWh_p50"].max())
    peak_hour_load = peak_machine_load + baseline

    machine_utilization = (total_active_slots / (len(mids) * makespan_slots)) * 100.0
    total_idle_time = (len(mids) * makespan_slots - total_active_slots) * config.SLOT_DURATION_MIN

    return {
        "Total_Energy_Cost_INR": round(total_energy_cost, 2),
        "Peak_Hour_Load_kW": round(peak_hour_load, 2),
        "Makespan_min": float(makespan_slots * config.SLOT_DURATION_MIN),
        "Makespan_hours": round(makespan_slots * config.SLOT_DURATION_MIN / 60.0, 2),
        "Machine_Utilization_pct": round(machine_utilization, 2),
        "Average_Waiting_Time_min": round(total_waiting_time / len(schedule_df), 2),
        "Total_Idle_Time_min": float(total_idle_time),
        "Total_Delay_min": float(total_delay),
        "Late_Jobs": int(late_jobs_count),
        "On_Time_Completion_pct": round((1 - late_jobs_count / len(schedule_df)) * 100.0, 2),
        "Total_Carbon_Emissions_tCO2": round(total_carbon, 4),
        "Total_Power_Factor_Penalty_INR": round(total_pf_penalty, 2),
    }
