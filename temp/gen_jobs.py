"""
Generates job_table.csv with 100 jobs designed to show clear energy optimization.
Produces the exact same CSV column format as the existing job_table.csv.
"""
import random
import csv
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

random.seed(42)

machines = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
priorities = ["High", "Medium", "Low"]
base_date = datetime(2026, 1, 1)

# Peak hours: 08:00 - 20:00 (slots 32-80 in a 96-slot day)
# Off-peak:   20:00 - 08:00 (slots 80-96 + 0-32)

jobs = []
for i in range(1, 101):
    job_id = f"J{i}"

    # Arrivals: spread 04:00 - 18:00
    # Mix: 60% during peak (08:00-18:00), 40% early morning (04:00-08:00)
    if random.random() < 0.6:
        # Peak-hour arrival (can be shifted off-peak)
        arr_hour = random.randint(8, 18)
    else:
        # Early arrival (already near off-peak, FCFS might schedule off-peak anyway)
        arr_hour = random.randint(4, 8)

    arr_min = random.choice([0, 15, 30, 45])
    arrival = base_date + timedelta(hours=arr_hour, minutes=arr_min)

    # Duration: 30 to 150 min (realistic steel plant jobs)
    duration_min = random.choice([30, 45, 60, 75, 90, 105, 120, 135, 150])

    # Deadline: 12-30 hours after arrival
    # Wide enough: even a peak-arriving job can shift to off-peak (20:00) same day
    deadline_hours = random.randint(12, 30)
    deadline = arrival + timedelta(hours=deadline_hours)

    # Priority
    priority = random.choices(priorities, weights=[0.3, 0.5, 0.2], k=1)[0]

    # Compatible machines: 2-4 random machines
    num_compat = random.randint(2, 4)
    compatible = sorted(random.sample(machines, num_compat))
    compatible_str = ",".join(compatible)

    # Format: match existing CSV exactly
    arrival_str = arrival.strftime("%Y-%m-%d %H:%M")
    deadline_str = deadline.strftime("%Y-%m-%d %H:%M")

    jobs.append({
        "Job_ID": job_id,
        "Duration_min": duration_min,
        "Deadline": deadline_str,
        "Priority": priority,
        "Compatible_Machines": compatible_str,
        "Arrival_Time": arrival_str,
    })

output_path = os.path.join(os.path.dirname(__file__), '..', 'job_table.csv')
fieldnames = ["Job_ID", "Duration_min", "Deadline", "Priority", "Compatible_Machines", "Arrival_Time"]

with open(output_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for job in jobs:
        writer.writerow(job)

print(f"SUCCESS: Written {len(jobs)} jobs to {os.path.abspath(output_path)}")
for job in jobs[:5]:
    print(f"  {job}")
