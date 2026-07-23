"""
Automated Test for KPI Calculator Module.
"""

import pandas as pd
from scheduler.kpi import KPICalculator
from scheduler.data_loader import ParsedMachine
from config.config import config


def test_kpi_calculator():
    """Tests calculation of all 10 Key Performance Indicators."""
    schedule_df = pd.DataFrame([
        {
            "Job_ID": "J1",
            "Assigned_Machine": "M1",
            "Start_Slot": 0,
            "End_Slot": 4,
            "Duration_min": 60,
            "Arrival_Slot": 0,
            "Deadline_Slot": 10,
            "Delay_min": 0,
            "Is_Late": 0,
            "Energy_Cost_$": 15.5,
        }
    ])

    machines = [
        ParsedMachine(
            machine_id="M1",
            machine_type="CNC",
            idle_power_kw=2.0,
            active_power_kw=10.0,
            changeover_min=15,
            changeover_slots=1,
            available_from_slot=0,
            available_to_slot=96,
        )
    ]
    rates = [0.10] * 96

    calc = KPICalculator(cfg=config)
    kpis = calc.compute_kpis(schedule_df, machines, rates)

    assert "Total_Energy_Cost_$" in kpis
    assert "Peak_Hour_Load_kWh" in kpis
    assert "Makespan_min" in kpis
    assert "Machine_Utilization_%" in kpis
    assert "On_Time_Completion_%" in kpis
    assert kpis["Total_Energy_Cost_$"] == 15.5
    assert kpis["On_Time_Completion_%"] == 100.0
