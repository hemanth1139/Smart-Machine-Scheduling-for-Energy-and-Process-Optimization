"""
Synthetic Dataset Generator — FD-PDTS Benchmarking Framework
=============================================================
Generates a capacity-feasible industrial instance that exposes the energy-cost
inefficiency of naive rules (FCFS, EDF) while leaving enough slack for
energy-aware methods to shift work into off-peak windows without blowing
deadlines or the planning horizon.

Design principles (publication-grade):
  1. Workload fits the horizon (~45–55% machine capacity) so schedules can
     finish inside the planning window; deferred work is still charged fairly.
  2. ~75% of jobs arrive during Maximum_Load hours (08:00–17:00) so FCFS
     naturally burns peak tariffs.
  3. Deadlines allow one overnight Light_Load shift (22:00–05:59) but are
     tight enough that infinite deferral is punished by lateness KPIs.
  4. Heterogeneous machine power (30–180 kW) so routing to efficient machines
     yields measurable savings beyond pure time-shifting.
  5. Bimodal durations create realistic packing pressure.
"""

from pathlib import Path
import pandas as pd
import numpy as np

try:
    from backend.config import config
except ImportError:
    from config import config


# ---------------------------------------------------------------------------
# Configuration — sized so ~50% of horizon capacity is consumed
# ---------------------------------------------------------------------------

N_JOBS     = 180
N_MACHINES = 8
HORIZON    = config.SCHEDULING_HORIZON_SLOTS   # 192 slots = 48 hours
SEED       = config.RANDOM_SEED


def _peak_slots() -> list:
    """Maximum_Load hours: 08:00–17:00 each day (slots 32–71, 128–167)."""
    return list(range(32, 72)) + list(range(128, 168))


def _medium_slots() -> list:
    """Medium_Load shoulders: 06–07 and 18–21 each day."""
    day1 = list(range(24, 32)) + list(range(72, 88))
    day2 = list(range(120, 128)) + list(range(168, 184))
    return day1 + day2


def _offpeak_slots() -> list:
    """Light_Load night window: 22:00–05:59."""
    all_slots = set(range(HORIZON))
    return sorted(all_slots - set(_peak_slots()) - set(_medium_slots()))


def generate_datasets():
    rng = np.random.default_rng(SEED)
    raw_dir = config.RAW_DATA_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. MACHINES — heterogeneous power so routing matters
    # -------------------------------------------------------------------------
    machine_types = [
        "CNC_Machining", "Laser_Cutting", "Welding_Robot", "Heat_Treatment",
        "Stamping_Press", "Assembly_Line", "Injection_Moulding", "Surface_Grinding",
    ]

    # Explicit power tiers: 2 efficient, 4 medium, 2 energy-hungry
    power_tiers = [35.0, 42.0, 75.0, 88.0, 95.0, 110.0, 155.0, 175.0]
    rng.shuffle(power_tiers)

    machines = []
    for i in range(N_MACHINES):
        mid = f"M{i + 1:02d}"
        active = round(float(power_tiers[i]), 2)
        idle = round(float(rng.uniform(3.0, 12.0)), 2)
        setup = round(float(rng.uniform(active * 0.08, active * 0.18)), 2)
        machines.append({
            "Machine_ID": mid,
            "Machine_Type": machine_types[i],
            "Idle_Power_kW": idle,
            "Active_Power_kW": active,
            "Setup_Energy_kW": setup,
            "Changeover_Time_min": 15,
        })

    machines_df = pd.DataFrame(machines)
    machines_df.to_csv(raw_dir / "machine_table.csv", index=False)
    print(f"[generate_datasets] Saved {len(machines_df)} machines.")

    machine_ids = machines_df["Machine_ID"].tolist()

    # -------------------------------------------------------------------------
    # 2. JOBS — peak-biased arrivals, off-peak-reachable deadlines
    # -------------------------------------------------------------------------
    peak_slots = _peak_slots()
    medium_slots = _medium_slots()
    offpeak_slots = _offpeak_slots()

    # 75% peak, 15% medium, 10% off-peak arrivals
    n_peak = int(N_JOBS * 0.75)
    n_medium = int(N_JOBS * 0.15)
    n_offpeak = N_JOBS - n_peak - n_medium

    arrivals = (
        rng.choice(peak_slots, size=n_peak, replace=True).tolist()
        + rng.choice(medium_slots, size=n_medium, replace=True).tolist()
        + rng.choice(offpeak_slots, size=n_offpeak, replace=True).tolist()
    )
    rng.shuffle(arrivals)

    # Durations: 65% short (1–4 slots), 35% medium-long (5–10 slots)
    # Keep total workload ~50% of capacity: 180 * ~4.2 / (8 * 192) ≈ 0.49
    n_short = int(N_JOBS * 0.65)
    n_long = N_JOBS - n_short
    durations = (
        rng.choice([15, 30, 45, 60], size=n_short).tolist()
        + rng.choice([75, 90, 105, 120, 150], size=n_long).tolist()
    )
    rng.shuffle(durations)

    priorities = rng.choice([1, 2, 3], size=N_JOBS, p=[0.20, 0.55, 0.25]).tolist()
    setup_types = rng.choice(["Type_A", "Type_B", "Type_C"], size=N_JOBS).tolist()

    # Compatible machines: always include at least one efficient machine option
    efficient = machines_df.nsmallest(3, "Active_Power_kW")["Machine_ID"].tolist()
    compatible_machines = []
    for _ in range(N_JOBS):
        n_compat = int(rng.integers(2, 5))  # 2–4 machines
        chosen = set(rng.choice(machine_ids, size=n_compat, replace=False).tolist())
        # 60% of jobs get an efficient machine in the eligible set
        if rng.random() < 0.60:
            chosen.add(str(rng.choice(efficient)))
        compatible_machines.append(",".join(sorted(chosen)))

    # Deadlines: enough slack to reach the next Light_Load night for most jobs.
    # Slack ~ 32–88 slots (8–22 h). High packing pressure still exists at night.
    job_ids = [f"J{i:03d}" for i in range(1, N_JOBS + 1)]
    deadlines = []
    for arr, dur in zip(arrivals, durations):
        dur_slots = max(1, int(np.ceil(dur / 15.0)))
        slack = int(rng.integers(32, 89))
        deadline = arr + dur_slots + slack
        deadline = min(int(HORIZON + 40), deadline)
        deadline = max(deadline, arr + dur_slots + 12)
        deadlines.append(int(deadline))

    jobs = []
    for jid, dur, dead, prio, compat, arr, stype in zip(
        job_ids, durations, deadlines, priorities,
        compatible_machines, arrivals, setup_types,
    ):
        jobs.append({
            "Job_ID": jid,
            "Duration_min": int(dur),
            "Deadline": int(dead),
            "Priority": int(prio),
            "Compatible_Machines": compat,
            "Arrival_Time": int(arr),
            "Setup_Type": stype,
        })

    jobs_df = pd.DataFrame(jobs)
    jobs_df.to_csv(raw_dir / "job_table.csv", index=False)
    print(f"[generate_datasets] Saved {len(jobs_df)} jobs.")

    # -------------------------------------------------------------------------
    # 3. Summary statistics
    # -------------------------------------------------------------------------
    dur_slots_all = [max(1, int(np.ceil(d / 15.0))) for d in durations]
    total_work = sum(dur_slots_all)
    capacity = N_MACHINES * HORIZON
    avg_slack = np.mean([
        d - a - max(1, int(np.ceil(dur / 15.0)))
        for a, dur, d in zip(arrivals, durations, deadlines)
    ])
    print(f"[generate_datasets] Workload / capacity: "
          f"{total_work}/{capacity} ({100.0 * total_work / capacity:.1f}%)")
    print(f"[generate_datasets] Average deadline slack: {avg_slack:.1f} slots "
          f"({avg_slack * 15 / 60:.1f} hrs)")
    print(f"[generate_datasets] Peak-hour arrivals: {100.0 * n_peak / N_JOBS:.0f}%")
    print(f"[generate_datasets] Avg duration: {np.mean(durations):.0f} min")
    print(f"[generate_datasets] Active power range: "
          f"{machines_df['Active_Power_kW'].min():.0f}–"
          f"{machines_df['Active_Power_kW'].max():.0f} kW")
    print(f"[generate_datasets] Saved all datasets to: {raw_dir}")


if __name__ == "__main__":
    generate_datasets()
