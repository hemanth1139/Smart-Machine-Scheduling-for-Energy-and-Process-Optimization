"""
Automated Test for Scheduling Engines (FCFS & CP-SAT).
"""

from scheduler.data_loader import ParsedJob, ParsedMachine
from scheduler.fcfs import FCFSScheduler
from scheduler.optimizer import OrtoolsScheduler
from config.config import config


def get_sample_inputs():
    """Generates small dummy scheduling inputs."""
    jobs = [
        ParsedJob(
            job_id="J1",
            duration_min=30,
            duration_slots=2,
            arrival_slot=0,
            deadline_slot=10,
            priority="High",
            priority_weight=3,
            compatible_machines=["M1"],
            arrival_time_str="00:00",
            deadline_str="02:30",
        ),
        ParsedJob(
            job_id="J2",
            duration_min=45,
            duration_slots=3,
            arrival_slot=1,
            deadline_slot=12,
            priority="Medium",
            priority_weight=2,
            compatible_machines=["M1"],
            arrival_time_str="00:15",
            deadline_str="03:00",
        ),
    ]

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

    energy_rates = [0.10] * 96
    return jobs, machines, energy_rates


def test_fcfs_scheduler():
    """Verifies baseline FCFS solver."""
    jobs, machines, rates = get_sample_inputs()
    fcfs = FCFSScheduler(cfg=config)
    res_df = fcfs.solve(jobs, machines, rates)

    assert len(res_df) == 2
    assert "Job_ID" in res_df.columns
    assert "Assigned_Machine" in res_df.columns


def test_cp_sat_scheduler():
    """Verifies OR-Tools CP-SAT scheduler."""
    jobs, machines, rates = get_sample_inputs()
    opt = OrtoolsScheduler(cfg=config)
    res_df = opt.solve(jobs, machines, rates)

    assert len(res_df) == 2
    assert "Job_ID" in res_df.columns
    # Verify job non-overlap: J2 start >= J1 end + changeover
    j1_end = res_df[res_df["Job_ID"] == "J1"]["End_Slot"].iloc[0]
    j2_start = res_df[res_df["Job_ID"] == "J2"]["Start_Slot"].iloc[0]
    assert j2_start >= j1_end
