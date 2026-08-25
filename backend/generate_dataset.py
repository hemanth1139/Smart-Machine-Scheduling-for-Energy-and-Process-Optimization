"""
Synthetic Dataset Generator — FD-PDTS Benchmarking Framework
=============================================================
Generates 500 jobs and 10 machines designed to expose the energy-cost
inefficiency of naive scheduling rules (FCFS, EDF) and highlight the
gains achievable by the FD-PDTS algorithm.

Design principles (publication-grade):
  1. Machines: 10 machines with high active power (50–200 kW) so that
     tariff differences translate into large, measurable energy savings.
  2. Arrivals: 70% of jobs arrive during peak-tariff windows (08:00–18:00,
     slots 32–72 and 112–152) so that FCFS naturally schedules during
     expensive periods.
  3. Deadlines: arrival + duration + generous slack (48–120 slots / 12–30 hrs)
     so FD-PDTS has room to shift jobs into cheap off-peak windows without
     violating deadlines.  FCFS ignores this slack and schedules immediately.
  4. Durations: bimodal distribution (short 15–60 min and long 90–240 min)
     to create realistic throughput heterogeneity.
  5. Compatible machines: 2–5 machines per job (realistic routing flexibility).

Expected benchmark outcome:
  - FCFS: high energy cost (peak-hour scheduling), moderate on-time rate
  - EDF: better on-time rate, still ignores energy
  - FD-PDTS: best energy cost and CO2, competitive on-time rate
  - Hybrid: further improvement over FD-PDTS via CP-SAT refinement
"""

from pathlib import Path
import pandas as pd
import numpy as np

from backend.config import config


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N_JOBS     = 500
N_MACHINES = 10                          # matches config
HORIZON    = config.SCHEDULING_HORIZON_SLOTS   # 192 slots = 48 hours
SEED       = config.RANDOM_SEED


def _peak_slots() -> list:
    """Return slot indices that fall in high-tariff windows (day shifts)."""
    # Day 1: 08:00–18:00 → slots 32–72
    # Day 2: 08:00–18:00 → slots 128–168  (32 + 96, 72 + 96)
    slots = list(range(32, 73)) + list(range(128, 169))
    return slots


def _offpeak_slots() -> list:
    """Return slot indices in cheap off-peak windows."""
    all_slots = set(range(HORIZON))
    return sorted(all_slots - set(_peak_slots()))


def generate_datasets():
    rng = np.random.default_rng(SEED)
    raw_dir = config.RAW_DATA_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. MACHINES — 10 machines, high-power industrial specs
    # -------------------------------------------------------------------------
    machine_types = [
        "CNC_Machining", "Laser_Cutting", "Welding_Robot", "Heat_Treatment",
        "Stamping_Press", "Assembly_Line", "Injection_Moulding",
        "Surface_Grinding", "Drilling_Centre", "Painting_Booth"
    ]

    machines = []
    for i in range(1, N_MACHINES + 1):
        mid   = f"M{i:02d}"
        mtype = machine_types[i - 1]

        # High active power (50–200 kW) → tariff differences are significant
        active  = round(float(rng.uniform(50.0, 200.0)), 2)
        idle    = round(float(rng.uniform(5.0, 20.0)), 2)
        # Setup energy proportional to active power
        setup   = round(float(rng.uniform(active * 0.1, active * 0.25)), 2)

        machines.append({
            "Machine_ID":          mid,
            "Machine_Type":        mtype,
            "Idle_Power_kW":       idle,
            "Active_Power_kW":     active,
            "Setup_Energy_kW":     setup,
            "Changeover_Time_min": 15
        })

    machines_df = pd.DataFrame(machines)
    machines_df.to_csv(raw_dir / "machine_table.csv", index=False)
    print(f"[generate_datasets] Saved {len(machines_df)} machines.")

    machine_ids = machines_df["Machine_ID"].tolist()

    # -------------------------------------------------------------------------
    # 2. JOBS — 500 jobs, peak-biased arrivals, generous deadlines
    # -------------------------------------------------------------------------

    # --- Arrival time distribution ---
    # 70% of jobs arrive during peak windows → FCFS schedules them at peak cost
    # 30% arrive off-peak → provides baseline diversity
    peak_slots    = _peak_slots()
    offpeak_slots = _offpeak_slots()

    n_peak    = int(N_JOBS * 0.70)
    n_offpeak = N_JOBS - n_peak

    arrivals_peak    = rng.choice(peak_slots, size=n_peak, replace=True).tolist()
    arrivals_offpeak = rng.choice(offpeak_slots, size=n_offpeak, replace=True).tolist()
    all_arrivals     = arrivals_peak + arrivals_offpeak
    rng.shuffle(all_arrivals)   # mix them up so FCFS gets a mixed stream

    # --- Duration distribution (bimodal: short and long jobs) ---
    # 60% short (15–60 min = 1–4 slots), 40% long (90–240 min = 6–16 slots)
    n_short = int(N_JOBS * 0.60)
    n_long  = N_JOBS - n_short

    durations_short = rng.choice([15, 30, 45, 60], size=n_short).tolist()
    durations_long  = rng.choice([90, 120, 150, 180, 210, 240], size=n_long).tolist()
    all_durations   = durations_short + durations_long
    rng.shuffle(all_durations)

    # --- Priority ---
    # 20% High, 60% Medium, 20% Low
    priorities = rng.choice([1, 2, 3], size=N_JOBS, p=[0.20, 0.60, 0.20]).tolist()

    # --- Setup types ---
    setup_types = rng.choice(["Type_A", "Type_B", "Type_C"], size=N_JOBS).tolist()

    # --- Compatible machines (2–5 per job) ---
    compatible_machines = []
    for _ in range(N_JOBS):
        n_compat = int(rng.integers(2, 6))          # 2, 3, 4, or 5
        chosen   = rng.choice(machine_ids, size=n_compat, replace=False).tolist()
        chosen.sort()
        compatible_machines.append(",".join(chosen))

    # --- Deadlines: generous slack so FD-PDTS can shift to off-peak ---
    # Slack = 48 to 120 slots (12–30 hours)
    # This ensures:
    #   - FCFS (which uses no slack awareness) still runs close to arrival
    #   - FD-PDTS can delay by up to 4 slots cheaply and still meet deadlines
    #   - EDF ordering is meaningful (varied deadlines)
    job_ids   = [f"J{i:03d}" for i in range(1, N_JOBS + 1)]
    deadlines = []
    for arr, dur in zip(all_arrivals, all_durations):
        dur_slots = max(1, int(np.ceil(dur / 15.0)))
        # Generous slack: 48–120 slots (12–30 hours)
        slack     = int(rng.integers(48, 121))
        # Deadline must not exceed horizon; clamp if needed but allow extension
        deadline  = arr + dur_slots + slack
        # Allow up to HORIZON * 1.5 to prevent all deadlines being clamped
        deadline  = min(int(HORIZON * 1.5), deadline)
        deadlines.append(int(deadline))

    jobs = []
    for jid, dur, dead, prio, compat, arr, stype in zip(
        job_ids, all_durations, deadlines, priorities,
        compatible_machines, all_arrivals, setup_types
    ):
        jobs.append({
            "Job_ID":               jid,
            "Duration_min":         int(dur),
            "Deadline":             int(dead),
            "Priority":             int(prio),
            "Compatible_Machines":  compat,
            "Arrival_Time":         int(arr),
            "Setup_Type":           stype
        })

    jobs_df = pd.DataFrame(jobs)
    jobs_df.to_csv(raw_dir / "job_table.csv", index=False)
    print(f"[generate_datasets] Saved {len(jobs_df)} jobs.")

    # -------------------------------------------------------------------------
    # 3. Summary statistics (for verification)
    # -------------------------------------------------------------------------
    avg_slack = np.mean([
        d - a - max(1, int(np.ceil(dur / 15.0)))
        for a, dur, d in zip(all_arrivals, all_durations, deadlines)
    ])
    pct_peak_arrivals = 100.0 * n_peak / N_JOBS
    print(f"[generate_datasets] Average deadline slack: {avg_slack:.1f} slots "
          f"({avg_slack * 15 / 60:.1f} hrs)")
    print(f"[generate_datasets] Peak-hour arrivals: {pct_peak_arrivals:.0f}%")
    print(f"[generate_datasets] Avg duration: {np.mean(all_durations):.0f} min")
    print(f"[generate_datasets] Avg active power: "
          f"{machines_df['Active_Power_kW'].mean():.1f} kW")
    print(f"[generate_datasets] Saved all datasets to: {raw_dir}")


if __name__ == "__main__":
    generate_datasets()
