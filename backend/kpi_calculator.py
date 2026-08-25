"""
KPI Calculation Engine.
Computes comprehensive operational, economic, and environmental metrics.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from backend.config import config


def compute_schedule_kpis(
    schedule_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    forecast_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Computes KPIs dynamically for a given schedule.
    """
    kpis = {}
    
    # Check if empty
    if schedule_df.empty:
        return {
            "Total_Energy_Cost_INR": 0.0,
            "Peak_Hour_Load_kWh": 0.0,
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

    # Maps for lookup
    job_map = jobs_df.set_index("Job_ID").to_dict(orient="index")
    mach_map = machines_df.set_index("Machine_ID").to_dict(orient="index")
    
    horizon_slots = config.SCHEDULING_HORIZON_SLOTS
    
    # Active and Idle loads at each slot
    active_load_slots = np.zeros(horizon_slots)
    idle_load_slots = np.zeros(horizon_slots)
    
    # Initialize counts
    total_delay = 0.0
    late_jobs_count = 0
    total_waiting_time = 0.0
    
    # Setup mapping of machines running active vs idle
    machine_active_slots = {mid: np.zeros(horizon_slots) for mid in mach_map.keys()}
    
    for _, row in schedule_df.iterrows():
        jid = row["Job_ID"]
        mid = row["Machine_ID"]
        start_slot = int(row["Start_Slot"])
        end_slot = int(row["End_Slot"])
        
        j_p = job_map[jid]
        m_p = mach_map[mid]
        
        # Mark active slots for this machine within the horizon
        start_slot_clipped = min(horizon_slots, start_slot)
        end_slot_clipped = min(horizon_slots, end_slot)
        machine_active_slots[mid][start_slot_clipped:end_slot_clipped] = 1.0
        
        # Calculate delay
        deadline_slot = j_p["Deadline"]
        if end_slot > deadline_slot:
            total_delay += (end_slot - deadline_slot) * config.SLOT_DURATION_MIN
            late_jobs_count += 1
            
        # Calculate waiting time (start_slot - arrival_time)
        arrival_slot = j_p["Arrival_Time"]
        waiting_slots = max(0, start_slot - arrival_slot)
        total_waiting_time += waiting_slots * config.SLOT_DURATION_MIN

    # Calculate active power, idle power, costs, carbon, and power factor penalty at each slot
    total_energy_cost = 0.0
    total_carbon = 0.0
    total_pf_penalty = 0.0
    
    # Tariff rate list from forecast
    tariffs = np.zeros(horizon_slots)
    co2_rates = np.zeros(horizon_slots)
    pf_values = np.zeros(horizon_slots)
    
    for t in range(horizon_slots):
        f_row = forecast_df.iloc[t]
        load_type = f_row.get("Load_Type", "Light_Load")
        
        # Determine tariff
        if load_type == "Maximum_Load":
            tariffs[t] = config.TARIFF_MAX_LOAD
        elif load_type == "Medium_Load":
            tariffs[t] = config.TARIFF_MED_LOAD
        else:
            tariffs[t] = config.TARIFF_LIGHT_LOAD
            
        co2_rates[t] = f_row.get("predicted_CO2_p50", 0.05)
        pf_values[t] = f_row.get("predicted_PF_p50", 0.92)

    # Sum powers per slot
    for t in range(horizon_slots):
        slot_active_power = 0.0
        slot_idle_power = 0.0
        
        for mid, m_p in mach_map.items():
            if machine_active_slots[mid][t] == 1.0:
                # Active power kW
                slot_active_power += m_p["Active_Power_kW"]
            else:
                # Idle power kW
                slot_idle_power += m_p["Idle_Power_kW"]
                
        # 15-minute slot energy in kWh = kW * (15 / 60)
        slot_active_energy = slot_active_power * 0.25
        slot_idle_energy = slot_idle_power * 0.25
        slot_total_energy = slot_active_energy + slot_idle_energy
        
        active_load_slots[t] = slot_active_power
        idle_load_slots[t] = slot_idle_power
        
        # Calculate cost
        total_energy_cost += slot_total_energy * tariffs[t]
        
        # Calculate carbon (emissions = energy kWh * CO2 rate intensity)
        total_carbon += slot_total_energy * co2_rates[t]
        
        # Calculate Power Factor penalty
        pf_t = pf_values[t]
        if pf_t < 0.90:
            # Penalty proportional to active energy consumed * tariff * (0.90 - pf) * factor
            penalty_factor = 2.0
            total_pf_penalty += slot_total_energy * tariffs[t] * (0.90 - pf_t) * penalty_factor

    # Makespan = max end slot - min start slot (or just max end slot)
    max_end_slot = int(schedule_df["End_Slot"].max())
    min_start_slot = int(schedule_df["Start_Slot"].min())
    makespan_slots = max_end_slot - min_start_slot
    makespan_min = makespan_slots * config.SLOT_DURATION_MIN
    
    # Machine Utilization: average percentage of slots machines are active
    total_active_slots = 0.0
    for mid in mach_map.keys():
        total_active_slots += machine_active_slots[mid].sum()
    total_possible_slots = len(mach_map) * horizon_slots
    machine_utilization = (total_active_slots / total_possible_slots) * 100.0
    
    # Idle time
    total_idle_time = (total_possible_slots - total_active_slots) * config.SLOT_DURATION_MIN
    
    # Peak hour load: maximum load in any slot (kW)
    total_grid_load_slots = active_load_slots + forecast_df["predicted_kWh_p50"].values
    peak_hour_load = float(total_grid_load_slots.max())

    kpis["Total_Energy_Cost_INR"] = round(total_energy_cost, 2)
    kpis["Peak_Hour_Load_kW"] = round(peak_hour_load, 2)
    kpis["Makespan_min"] = float(makespan_min)
    kpis["Makespan_hours"] = round(makespan_min / 60.0, 2)
    kpis["Machine_Utilization_pct"] = round(machine_utilization, 2)
    kpis["Average_Waiting_Time_min"] = round(total_waiting_time / len(schedule_df), 2)
    kpis["Total_Idle_Time_min"] = float(total_idle_time)
    kpis["Total_Delay_min"] = float(total_delay)
    kpis["Late_Jobs"] = int(late_jobs_count)
    kpis["On_Time_Completion_pct"] = round((1 - late_jobs_count / len(schedule_df)) * 100.0, 2)
    kpis["Total_Carbon_Emissions_tCO2"] = round(total_carbon, 4)
    kpis["Total_Power_Factor_Penalty_INR"] = round(total_pf_penalty, 2)
    
    return kpis
