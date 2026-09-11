"""
Synthetic Dataset Generator v2 — FD-PDTS Benchmarking Framework
================================================================
Accepts a `seed` parameter so the pipeline can generate 20 independent
instances for multi-seed evaluation.

Per-seed variation (on top of the shared structural design principles):
  - N_JOBS sampled from [160, 165, 170, 175, 180, 185, 190, 195, 200]
  - Duration distribution bias varies (short/long split +/-5%)
  - Arrival peak fraction varies (70%-80%)
  - Deadline slack range shifts by seed (tighter/looser)
  - Machine power tier re-shuffled per seed
  - Compatibility ratio varies (2-5 compatible machines per job)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Tuple, Optional

try:
    from backend.config import config
except ImportError:
    from config import config


N_MACHINES = 8
HORIZON = config.SCHEDULING_HORIZON_SLOTS  # 192 slots = 48 hours


def _peak_slots() -> list:
    return list(range(32, 72)) + list(range(128, 168))


def _medium_slots() -> list:
    day1 = list(range(24, 32)) + list(range(72, 88))
    day2 = list(range(120, 128)) + list(range(168, 184))
    return day1 + day2


def _offpeak_slots() -> list:
    all_slots = set(range(HORIZON))
    return sorted(all_slots - set(_peak_slots()) - set(_medium_slots()))


def generate_datasets(
    seed: Optional[int] = None,
    save_to_disk: bool = True,
    raw_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate one scheduling instance.

    Args:
        seed:         Random seed. If None, uses config.RANDOM_SEED.
        save_to_disk: If True, writes CSV files to raw_dir.
        raw_dir:      Directory for CSV output. Defaults to config.RAW_DATA_DIR.

    Returns:
        (jobs_df, machines_df)
    """
    if seed is None:
        seed = config.RANDOM_SEED

    rng = np.random.default_rng(seed)

    if raw_dir is None:
        raw_dir = config.RAW_DATA_DIR
    raw_dir = Path(raw_dir)
    if save_to_disk:
        raw_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # Per-seed variation: N_JOBS sampled from a discrete range
    # --------------------------------------------------------------------------
    n_jobs_options = [160, 165, 170, 175, 180, 185, 190, 195, 200]
    # Use the seed to deterministically vary N_JOBS
    n_jobs = int(rng.choice(n_jobs_options))

    # --------------------------------------------------------------------------
    # 1. MACHINES
    # --------------------------------------------------------------------------
    machine_types = [
        "CNC_Machining", "Laser_Cutting", "Welding_Robot", "Heat_Treatment",
        "Stamping_Press", "Assembly_Line", "Injection_Moulding", "Surface_Grinding",
    ]
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
    if save_to_disk:
        machines_df.to_csv(raw_dir / "machine_table.csv", index=False)

    machine_ids = machines_df["Machine_ID"].tolist()

    # --------------------------------------------------------------------------
    # 2. JOBS — per-seed variation in peak fraction and duration split
    # --------------------------------------------------------------------------
    peak_slots = _peak_slots()
    medium_slots = _medium_slots()
    offpeak_slots = _offpeak_slots()

    # Peak fraction varies between 70% and 80% depending on seed
    peak_frac = float(rng.uniform(0.70, 0.80))
    medium_frac = float(rng.uniform(0.10, 0.18))
    offpeak_frac = 1.0 - peak_frac - medium_frac

    n_peak = int(n_jobs * peak_frac)
    n_medium = int(n_jobs * medium_frac)
    n_offpeak = n_jobs - n_peak - n_medium

    arrivals = (
        rng.choice(peak_slots, size=n_peak, replace=True).tolist()
        + rng.choice(medium_slots, size=n_medium, replace=True).tolist()
        + rng.choice(offpeak_slots, size=n_offpeak, replace=True).tolist()
    )
    rng.shuffle(arrivals)

    # Duration split varies between 60%-70% short
    short_frac = float(rng.uniform(0.60, 0.70))
    n_short = int(n_jobs * short_frac)
    n_long = n_jobs - n_short
    durations = (
        rng.choice([15, 30, 45, 60], size=n_short).tolist()
        + rng.choice([75, 90, 105, 120, 150], size=n_long).tolist()
    )
    rng.shuffle(durations)

    priorities = rng.choice([1, 2, 3], size=n_jobs, p=[0.20, 0.55, 0.25]).tolist()
    setup_types = rng.choice(["Type_A", "Type_B", "Type_C"], size=n_jobs).tolist()

    # Compatible machines: always include at least one efficient machine option
    efficient = machines_df.nsmallest(3, "Active_Power_kW")["Machine_ID"].tolist()
    compatible_machines = []
    for _ in range(n_jobs):
        n_compat = int(rng.integers(2, 5))
        chosen = set(rng.choice(machine_ids, size=n_compat, replace=False).tolist())
        if rng.random() < 0.60:
            chosen.add(str(rng.choice(efficient)))
        compatible_machines.append(",".join(sorted(chosen)))

    # Deadline slack varies per seed: range [28, 100] on average, ± ~8 slots
    slack_lo = int(rng.integers(24, 36))
    slack_hi = int(rng.integers(80, 100))

    job_ids = [f"J{i:03d}" for i in range(1, n_jobs + 1)]
    deadlines = []
    for arr, dur in zip(arrivals, durations):
        dur_slots = max(1, int(np.ceil(dur / 15.0)))
        slack = int(rng.integers(slack_lo, slack_hi + 1))
        deadline = arr + dur_slots + slack
        deadline = min(int(HORIZON + 40), deadline)
        deadline = max(deadline, arr + dur_slots + 12)
        deadlines.append(int(deadline))

    jobs = []
    for jid, dur, dead, prio, compat, arr, stype in zip(
        job_ids, durations, deadlines, priorities, compatible_machines, arrivals, setup_types
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
    if save_to_disk:
        jobs_df.to_csv(raw_dir / "job_table.csv", index=False)

    dur_slots_all = [max(1, int(np.ceil(d / 15.0))) for d in durations]
    total_work = sum(dur_slots_all)
    capacity = N_MACHINES * HORIZON
    print(
        f"[generate_datasets] seed={seed} | jobs={n_jobs} | "
        f"workload={total_work}/{capacity} ({100.0*total_work/capacity:.1f}%) | "
        f"peak_frac={peak_frac:.0%} | slack=[{slack_lo},{slack_hi}] | "
        f"power=[{machines_df['Active_Power_kW'].min():.0f},{machines_df['Active_Power_kW'].max():.0f}] kW"
    )

    return jobs_df, machines_df


if __name__ == "__main__":
    generate_datasets(seed=config.RANDOM_SEED, save_to_disk=True)
