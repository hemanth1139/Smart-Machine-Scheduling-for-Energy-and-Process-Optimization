import pandas as pd
from pathlib import Path

def generate_datasets():
    # Define project root and directories
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # ---------------------------------------------------------
    # MACHINE TABLE GENERATION
    # ---------------------------------------------------------
    # M1: Welding (Medium Power, Medium Changeover)
    # M2: Lathe (High Power, High Changeover)
    # M3: CNC (Medium Power, Low Changeover)
    # M4: Drilling (Low Power, Low Changeover) - highly efficient!
    machines = [
        {
            "Machine_ID": "M1",
            "Machine_Type": "Welding",
            "Idle_Power_kW": 2.0,
            "Active_Power_kW": 20.0,
            "Changeover_Time_min": 15,
            "Available_From": "00:00",
            "Available_To": "23:59"
        },
        {
            "Machine_ID": "M2",
            "Machine_Type": "Lathe",
            "Idle_Power_kW": 2.5,
            "Active_Power_kW": 25.0,
            "Changeover_Time_min": 30,
            "Available_From": "00:00",
            "Available_To": "23:59"
        },
        {
            "Machine_ID": "M3",
            "Machine_Type": "CNC",
            "Idle_Power_kW": 1.5,
            "Active_Power_kW": 12.0,
            "Changeover_Time_min": 15,
            "Available_From": "00:00",
            "Available_To": "23:59"
        },
        {
            "Machine_ID": "M4",
            "Machine_Type": "Drilling",
            "Idle_Power_kW": 0.5,
            "Active_Power_kW": 5.0,
            "Changeover_Time_min": 15,
            "Available_From": "00:00",
            "Available_To": "23:59"
        }
    ]
    
    machine_df = pd.DataFrame(machines)
    
    # ---------------------------------------------------------
    # JOB TABLE GENERATION
    # ---------------------------------------------------------
    jobs = []
    
    # Scenario 1: Peak Energy Shifting & Machine Choice (J1 to J6)
    # Arrive at 07:00 (just before peak hours 08:00 - 20:00). Loose deadlines.
    # Compatible with M2 (25kW) and M4 (5kW).
    # FCFS: Schedules immediately, loading up M2 and M4 in peak hours ($0.25).
    # CP-SAT: Shifts J1-J6 to off-peak slots (before 08:00, after 20:00) and routes them to M4.
    for i in range(1, 7):
        jobs.append({
            "Job_ID": f"J{i}",
            "Duration_min": 60,
            "Deadline": "2026-01-01 22:00",
            "Priority": "Medium",
            "Compatible_Machines": "M2,M4",
            "Arrival_Time": "2026-01-01 07:00"
        })
        
    # Scenario 2: Priority Blocking / Tardiness Prevention (J7 to J11)
    # Long, low-priority job J7 arrives at 06:00.
    # Four short, high-priority jobs J8-J11 arrive at 06:15 with tight deadlines (09:00).
    # FCFS: Runs J7 first on M3, blocking M3 from 06:00 to 14:00. J8-J11 are extremely late.
    # CP-SAT: Runs J8-J11 first (06:15 to 08:15, all on-time), then runs J7 (08:15 to 16:15, on-time).
    jobs.append({
        "Job_ID": "J7",
        "Duration_min": 480, # 8 hours
        "Deadline": "2026-01-01 23:00",
        "Priority": "Low",
        "Compatible_Machines": "M3",
        "Arrival_Time": "2026-01-01 06:00"
    })
    for i in range(8, 12):
        jobs.append({
            "Job_ID": f"J{i}",
            "Duration_min": 30,
            "Deadline": "2026-01-01 09:00",
            "Priority": "High",
            "Compatible_Machines": "M3",
            "Arrival_Time": "2026-01-01 06:15"
        })
        
    # Scenario 3: Machine Routing & Active Power Efficiency (J12 to J15)
    # Arrive at 08:00. Deadline is 18:00 (72 slots).
    # Compatible with M1 (20kW) and M4 (5kW).
    # FCFS: Schedules on whichever is available, splitting jobs between M1 and M4.
    # CP-SAT: Recognizes M4 is 4x more energy efficient and has enough capacity, routes all 4 to M4.
    for i in range(12, 16):
        jobs.append({
            "Job_ID": f"J{i}",
            "Duration_min": 120, # 2 hours
            "Deadline": "2026-01-01 18:00",
            "Priority": "Medium",
            "Compatible_Machines": "M1,M4",
            "Arrival_Time": "2026-01-01 08:00"
        })
        
    job_df = pd.DataFrame(jobs)
    
    # Save to both project root and data/raw/
    machine_df.to_csv(project_root / "machine_table.csv", index=False)
    job_df.to_csv(project_root / "job_table.csv", index=False)
    
    machine_df.to_csv(raw_dir / "machine_table.csv", index=False)
    job_df.to_csv(raw_dir / "job_table.csv", index=False)
    
    print(f"Generated {len(jobs)} jobs and {len(machines)} machines.")
    print(f"Saved datasets to project root and {raw_dir}")

if __name__ == "__main__":
    generate_datasets()
