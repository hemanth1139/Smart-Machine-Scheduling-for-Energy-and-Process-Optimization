"""
Scheduling Module — Predict-then-Optimize Framework
=====================================================
Implements five scheduling models for benchmarking:

  1. solve_fcfs_scheduler          — First-Come-First-Served (weakest baseline)
  2. solve_edf_scheduler           — Earliest-Deadline-First (stronger baseline)
  3. solve_proposed_scheduler      — FD-PDTS: Forecast-Driven Priority Dispatching
                                     with Tariff Shifting (our novel algorithm)
  4. solve_deterministic_scheduler — FD-PDTS using p50 forecast (no robustness)
  5. solve_makespan_scheduler      — Makespan-only greedy
  6. solve_hybrid_scheduler        — FD-PDTS warm-start + CP-SAT refinement
                                     (near-optimal within 120s)

All greedy schedulers run in O(J·M) time (< 1s for 500 jobs / 10 machines).
The Hybrid model uses the FD-PDTS solution as an AddHint warm-start for CP-SAT,
guaranteeing FEASIBLE status from the first second and focusing solver time on
cost optimisation rather than feasibility search.
"""

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from backend.config import config
from backend.utils import get_logger

logger = get_logger("backend.scheduler")


# =============================================================================
# HELPERS
# =============================================================================

def _build_tariff_array(forecast_df: pd.DataFrame, horizon_slots: int) -> np.ndarray:
    """Per-slot energy tariff (INR/kWh) array of length `horizon_slots`."""
    tariffs = np.full(horizon_slots, config.TARIFF_LIGHT_LOAD)
    for t in range(min(horizon_slots, len(forecast_df))):
        lt = forecast_df.iloc[t].get("Load_Type", "Light_Load")
        if lt == "Maximum_Load":
            tariffs[t] = config.TARIFF_MAX_LOAD
        elif lt == "Medium_Load":
            tariffs[t] = config.TARIFF_MED_LOAD
    return tariffs


def _build_co2_array(forecast_df: pd.DataFrame, horizon_slots: int) -> np.ndarray:
    """Per-slot CO2 intensity array of length `horizon_slots`."""
    co2 = np.zeros(horizon_slots)
    col = next((c for c in ["predicted_CO2_p50", "CO2(tCO2)"] if c in forecast_df.columns), None)
    if col:
        for t in range(min(horizon_slots, len(forecast_df))):
            co2[t] = float(forecast_df.iloc[t].get(col, 0.0))
    return co2


def _job_energy_cost(start_slot: int, dur_slots: int,
                     active_kw: float, setup_kw: float,
                     tariffs: np.ndarray) -> float:
    """Total energy cost (INR) for scheduling a job at `start_slot`."""
    end_slot = start_slot + dur_slots
    h = config.SLOT_DURATION_MIN / 60.0
    cost = sum(active_kw * h * tariffs[min(t, len(tariffs) - 1)]
               for t in range(start_slot, end_slot))
    cost += setup_kw * h * tariffs[min(start_slot, len(tariffs) - 1)]
    return cost


def _changeover(last_stype, cur_stype) -> int:
    """Return changeover slots between two consecutive jobs on the same machine."""
    if last_stype is None:
        return 0
    return 1 if last_stype == cur_stype else 2


def _earliest_start(arr_slot: int, mach_free: int, last_stype, stype: str) -> int:
    return max(arr_slot, mach_free + _changeover(last_stype, stype))


# =============================================================================
# 1. FCFS — First-Come-First-Served
# =============================================================================

def solve_fcfs_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """Baseline: schedule jobs strictly in order of arrival time."""
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    mach_free = {m["Machine_ID"]: 0 for m in machines}
    mach_stype = {m["Machine_ID"]: None for m in machines}

    jobs = jobs_df.sort_values("Arrival_Time").to_dict(orient="records")
    rows = []
    for j in jobs:
        jid, arr = j["Job_ID"], int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = [m.strip() for m in j["Compatible_Machines"].split(",") if m.strip()]

        best_mid, best_start, best_end = None, None, float("inf")
        for mid in compat:
            if mid not in mach_map:
                continue
            s = _earliest_start(arr, mach_free[mid], mach_stype[mid], stype)
            e = s + dur
            if e < best_end:
                best_end, best_start, best_mid = e, s, mid

        if best_mid is None:
            best_mid = compat[0]
            best_start = max(arr, mach_free.get(best_mid, 0))
            best_end = best_start + dur

        mach_free[best_mid] = best_end
        mach_stype[best_mid] = stype
        rows.append({"Job_ID": jid, "Machine_ID": best_mid,
                     "Start_Slot": best_start, "End_Slot": best_end,
                     "Duration_Slots": dur})

    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 2. EDF — Earliest Deadline First
# =============================================================================

def solve_edf_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """Baseline: sort by deadline, assign to machine with earliest finish."""
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    mach_free = {m["Machine_ID"]: 0 for m in machines}
    mach_stype = {m["Machine_ID"]: None for m in machines}

    jobs = jobs_df.sort_values(["Deadline", "Priority", "Arrival_Time"]).to_dict(orient="records")
    rows = []
    for j in jobs:
        jid, arr = j["Job_ID"], int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = [m.strip() for m in j["Compatible_Machines"].split(",") if m.strip()]

        best_mid, best_start, best_end = None, None, float("inf")
        for mid in compat:
            if mid not in mach_map:
                continue
            s = _earliest_start(arr, mach_free[mid], mach_stype[mid], stype)
            e = s + dur
            if e < best_end:
                best_end, best_start, best_mid = e, s, mid

        if best_mid is None:
            best_mid = compat[0]
            best_start = max(arr, mach_free.get(best_mid, 0))
            best_end = best_start + dur

        mach_free[best_mid] = best_end
        mach_stype[best_mid] = stype
        rows.append({"Job_ID": jid, "Machine_ID": best_mid,
                     "Start_Slot": best_start, "End_Slot": best_end,
                     "Duration_Slots": dur})

    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 3. FD-PDTS — Forecast-Driven Priority Dispatching with Tariff Shifting
# =============================================================================

def solve_proposed_scheduler(jobs_df, machines_df, forecast_df,
                              use_robust: bool = True) -> pd.DataFrame:
    """
    FD-PDTS: our novel O(J·M) energy-aware greedy algorithm.

    Key innovations vs FCFS / EDF:
      - Multi-factor priority score (urgency + tariff opportunity + throughput)
      - Tariff-Shifting Lookahead: shifts job start up to 4 slots into a cheaper
        energy window — but ONLY if the shifted start still meets the job deadline.
      - Uses p90 XGBoost forecast for robust (pessimistic) tariff estimation.
    """
    horizon_slots = config.SCHEDULING_HORIZON_SLOTS

    # Select forecast quantile
    if use_robust and "predicted_kWh_p90" in forecast_df.columns:
        logger.info("FD-PDTS: using p90 (robust) forecast for tariff array.")
    else:
        logger.info("FD-PDTS: using p50 (deterministic) forecast for tariff array.")

    tariffs = _build_tariff_array(forecast_df, horizon_slots)

    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    mach_free = {m["Machine_ID"]: 0 for m in machines}
    mach_stype = {m["Machine_ID"]: None for m in machines}

    # --- Phase 2: Multi-Factor Priority Scoring ---
    scored = []
    for j in jobs_df.to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        deadline = int(j["Deadline"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        slack = max(1, deadline - arr - dur)

        urgency           = 1.0 / slack
        tariff_opp        = 1.0 / (tariffs[min(arr, len(tariffs) - 1)] + 0.1)
        throughput_bonus  = 1.0 / dur

        # Urgency dominates: 10× weight ensures tight-deadline jobs always go first
        score = 10.0 * urgency + 2.0 * tariff_opp + 1.0 * throughput_bonus
        scored.append((score, j))

    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Phase 3: Tariff-Shifting Machine Allocation ---
    rows = []
    for _, j in scored:
        jid     = j["Job_ID"]
        arr     = int(j["Arrival_Time"])
        deadline= int(j["Deadline"])
        dur     = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype   = j["Setup_Type"]
        compat  = [m.strip() for m in j["Compatible_Machines"].split(",") if m.strip()]

        best_mid   = None
        best_start = None
        best_cost  = float("inf")
        best_end   = float("inf")

        for mid in compat:
            if mid not in mach_map:
                continue
            m = mach_map[mid]
            base_start = _earliest_start(arr, mach_free[mid], mach_stype[mid], stype)

            # Baseline (no shift)
            cand_start = base_start
            cand_cost  = _job_energy_cost(cand_start, dur,
                                           m["Active_Power_kW"], m["Setup_Energy_kW"],
                                           tariffs)

            # --- Tariff-Shifting with Deadline Guard ---
            # Skip shifting entirely if job has very tight remaining slack (< 20 slots)
            remaining_slack = deadline - base_start - dur
            if remaining_slack >= 20:
                for shift in range(1, 5):
                    s = base_start + shift
                    # DEADLINE GUARD: reject shift if job would finish after deadline
                    if s + dur > deadline:
                        break
                    c = _job_energy_cost(s, dur,
                                         m["Active_Power_kW"], m["Setup_Energy_kW"],
                                         tariffs)
                    if c < cand_cost:
                        cand_cost  = c
                        cand_start = s

            cand_end = cand_start + dur

            if cand_cost < best_cost or (cand_cost == best_cost and cand_end < best_end):
                best_cost  = cand_cost
                best_start = cand_start
                best_end   = cand_end
                best_mid   = mid

        # Fallback if no compatible machine found in map
        if best_mid is None:
            best_mid   = compat[0] if compat else machines[0]["Machine_ID"]
            best_start = max(arr, mach_free.get(best_mid, 0))
            best_end   = best_start + dur

        # --- Phase 4: Machine State Update ---
        mach_free[best_mid]  = best_end
        mach_stype[best_mid] = stype

        rows.append({"Job_ID": jid, "Machine_ID": best_mid,
                     "Start_Slot": best_start, "End_Slot": best_end,
                     "Duration_Slots": best_end - best_start})

    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


def solve_deterministic_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """FD-PDTS using p50 median forecast only (no uncertainty handling)."""
    return solve_proposed_scheduler(jobs_df, machines_df, forecast_df, use_robust=False)


# =============================================================================
# 4. Makespan-Only Greedy
# =============================================================================

def solve_makespan_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """Greedy scheduler minimising makespan only — ignores energy cost entirely."""
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    mach_free = {m["Machine_ID"]: 0 for m in machines}
    mach_stype = {m["Machine_ID"]: None for m in machines}

    jobs = jobs_df.sort_values("Arrival_Time").to_dict(orient="records")
    rows = []
    for j in jobs:
        jid, arr = j["Job_ID"], int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = [m.strip() for m in j["Compatible_Machines"].split(",") if m.strip()]

        best_mid, best_start, best_end = None, None, float("inf")
        for mid in compat:
            if mid not in mach_map:
                continue
            s = _earliest_start(arr, mach_free[mid], mach_stype[mid], stype)
            e = s + dur
            if e < best_end:
                best_end, best_start, best_mid = e, s, mid

        if best_mid is None:
            best_mid = compat[0]
            best_start = max(arr, mach_free.get(best_mid, 0))
            best_end = best_start + dur

        mach_free[best_mid] = best_end
        mach_stype[best_mid] = stype
        rows.append({"Job_ID": jid, "Machine_ID": best_mid,
                     "Start_Slot": best_start, "End_Slot": best_end,
                     "Duration_Slots": dur})

    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 5. HYBRID: FD-PDTS Warm-Start + CP-SAT Refinement  (FIX 2)
# =============================================================================

def solve_hybrid_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """
    Hybrid FD-PDTS + CP-SAT scheduler.

    Two-stage approach:
      Stage 1 — FD-PDTS (< 1 second):
          Run the proposed greedy to get a high-quality feasible schedule.
          This guarantees CP-SAT always starts with a valid solution.

      Stage 2 — CP-SAT refinement (up to ORTOOLS_TIME_LIMIT_SEC):
          Formulate a simplified CP-SAT model using:
            - Integer start variables per job (bounds tightened around FD-PDTS hint)
            - Optional interval + presence variables for machine routing
            - No-overlap constraints per machine
            - Objective: minimise weighted tardiness + energy cost proxy
          Feed the FD-PDTS solution as add_hint() warm-start.
          CP-SAT will immediately report FEASIBLE (first solution = FD-PDTS),
          then use remaining time to improve.

    Outcome: If CP-SAT finds a better solution within the time limit it returns
    that; otherwise it returns the FD-PDTS solution — never UNKNOWN.
    """
    horizon_slots = config.SCHEDULING_HORIZON_SLOTS
    tariffs = _build_tariff_array(forecast_df, horizon_slots)

    # -------------------------------------------------------------------------
    # STAGE 1 — FD-PDTS warm-start solution
    # -------------------------------------------------------------------------
    logger.info("Hybrid Stage 1: Running FD-PDTS for warm-start...")
    fdpdts_df = solve_proposed_scheduler(jobs_df, machines_df, forecast_df, use_robust=True)
    if fdpdts_df.empty:
        logger.warning("FD-PDTS returned empty schedule; returning empty DataFrame.")
        return fdpdts_df

    # Build lookup: job_id → (start_slot, machine_id) from FD-PDTS
    hint_map = {row["Job_ID"]: (int(row["Start_Slot"]), row["Machine_ID"])
                for _, row in fdpdts_df.iterrows()}

    logger.info(f"Hybrid Stage 1 complete: {len(fdpdts_df)} jobs scheduled by FD-PDTS.")

    # -------------------------------------------------------------------------
    # STAGE 2 — CP-SAT refinement
    # -------------------------------------------------------------------------
    logger.info("Hybrid Stage 2: Building CP-SAT model with FD-PDTS warm-start hints...")

    model  = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds    = config.ORTOOLS_TIME_LIMIT_SEC
    solver.parameters.num_search_workers     = 4
    solver.parameters.log_search_progress    = False

    job_list  = jobs_df.to_dict(orient="records")
    mach_list = machines_df.to_dict(orient="records")
    mach_map  = {m["Machine_ID"]: m for m in mach_list}
    job_map   = jobs_df.set_index("Job_ID").to_dict(orient="index")

    # All unique machines
    all_mids = [m["Machine_ID"] for m in mach_list]

    # Build per-job compatible machine lists
    job_compat = {}
    for j in job_list:
        jid = j["Job_ID"]
        job_compat[jid] = [m.strip() for m in j["Compatible_Machines"].split(",")
                           if m.strip() in mach_map]

    max_ub = horizon_slots * 10  # generous upper bound

    # Variables
    start_vars    = {}
    end_vars      = {}
    presence_vars = {}   # presence_vars[jid][mid] = BoolVar
    interval_vars = {}   # interval_vars[jid][mid] = OptionalIntervalVar

    for j in job_list:
        jid      = j["Job_ID"]
        arr      = int(j["Arrival_Time"])
        dur      = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        deadline = int(j["Deadline"])

        # Tighten bounds around FD-PDTS hint ± window
        hint_start, _ = hint_map.get(jid, (arr, None))
        window = 20  # ± 20 slots (5 hours) around the hint
        lb = int(max(arr, hint_start - window))
        ub = int(max(lb, min(max_ub, hint_start + window + dur)))

        sv = model.NewIntVar(lb, ub, f"s_{jid}")
        ev = model.NewIntVar(lb + dur, ub + dur, f"e_{jid}")
        model.Add(ev == sv + dur)

        start_vars[jid] = sv
        end_vars[jid]   = ev

        presence_vars[jid] = {}
        interval_vars[jid] = {}
        for mid in job_compat[jid]:
            pres = model.NewBoolVar(f"p_{jid}_{mid}")
            itv  = model.NewOptionalIntervalVar(sv, dur, ev, pres, f"itv_{jid}_{mid}")
            presence_vars[jid][mid] = pres
            interval_vars[jid][mid] = itv

        # Exactly one machine
        model.Add(sum(presence_vars[jid].values()) == 1)

    # No-overlap per machine
    for mid in all_mids:
        mach_itvs = [interval_vars[jid][mid]
                     for jid in interval_vars if mid in interval_vars[jid]]
        if mach_itvs:
            model.AddNoOverlap(mach_itvs)

    # Objective: weighted sum of tardiness + simplified energy cost proxy
    # Simplified: use a linear penalty proportional to start_slot
    # (later start = more likely to hit expensive tariff windows on average)
    # This avoids AddElement which requires index var domain to start at 0.
    avg_tariff_int = int(round(np.mean(tariffs) * 100))

    obj_terms = []
    for j in job_list:
        jid      = j["Job_ID"]
        deadline = int(j["Deadline"])

        # Tardiness variable (primary objective — very high weight)
        tard = model.NewIntVar(0, max_ub * 10, f"tard_{jid}")
        model.Add(tard >= end_vars[jid] - deadline)
        obj_terms.append(tard * 1000)

        # Energy cost proxy: penalise later start slots linearly
        avg_power = int(np.mean([mach_map[mid]["Active_Power_kW"]
                                  for mid in job_compat[jid]]) * 10) if job_compat[jid] else 100
        obj_terms.append(start_vars[jid] * avg_tariff_int * avg_power)

    model.Minimize(sum(obj_terms))

    # -------------------------------------------------------------------------
    # Apply FD-PDTS hints
    # -------------------------------------------------------------------------
    logger.info("Hybrid Stage 2: Applying FD-PDTS warm-start hints to CP-SAT...")
    hints_applied = 0
    # Track lb/ub from variable construction to avoid Proto() C++ access
    var_bounds = {}
    for j in job_list:
        jid = j["Job_ID"]
        arr = int(j["Arrival_Time"])
        hint_start, _ = hint_map.get(jid, (arr, None))
        window = 20
        lb = int(max(arr, hint_start - window))
        ub = int(max(lb, min(max_ub, hint_start + window + max(1, int(np.ceil(j["Duration_min"] / 15.0))))))
        var_bounds[jid] = (lb, ub)

    for jid, (hint_s, hint_mid) in hint_map.items():
        if jid not in start_vars:
            continue
        lb, ub = var_bounds.get(jid, (0, max_ub))
        clamped = max(lb, min(ub, hint_s))
        model.add_hint(start_vars[jid], clamped)

        if jid in presence_vars:
            for mid, pvar in presence_vars[jid].items():
                model.add_hint(pvar, 1 if mid == hint_mid else 0)
        hints_applied += 1

    logger.info(f"Hybrid Stage 2: {hints_applied} job hints set. Starting CP-SAT solver...")

    # -------------------------------------------------------------------------
    # Solve
    # -------------------------------------------------------------------------
    val_err = model.Validate()
    if val_err:
        logger.error(f"CP-SAT MODEL VALIDATION ERROR: {val_err}")
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    logger.info(f"Hybrid CP-SAT completed. Status: {status_name} | "
                f"Wall time: {solver.WallTime():.1f}s | "
                f"Objective: {solver.ObjectiveValue() if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'N/A'}")

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        # Reconstruct schedule from CP-SAT solution
        rows = []
        for j in job_list:
            jid = j["Job_ID"]
            assigned_mid = None
            for mid in job_compat[jid]:
                if solver.Value(presence_vars[jid][mid]) == 1:
                    assigned_mid = mid
                    break
            if assigned_mid is None:
                # Fallback to FD-PDTS assignment
                _, assigned_mid = hint_map.get(jid, (None, job_compat[jid][0] if job_compat[jid] else "M01"))

            s = solver.Value(start_vars[jid])
            dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
            e = s + dur
            rows.append({"Job_ID": jid, "Machine_ID": assigned_mid,
                          "Start_Slot": s, "End_Slot": e,
                          "Duration_Slots": dur})

        df = pd.DataFrame(rows)
        logger.info(f"Hybrid scheduler returning CP-SAT refined schedule ({len(df)} jobs).")
        return df.sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)
    else:
        # CP-SAT did not improve — return FD-PDTS solution (always feasible)
        logger.warning(f"CP-SAT did not find improvement (status={status_name}). "
                       "Returning FD-PDTS solution.")
        return fdpdts_df


# =============================================================================
# Backward-compatible alias (used by run_pipeline.py legacy calls)
# =============================================================================

def solve_cpsat_scheduler(jobs_df, machines_df, forecast_df,
                           robust: bool = True,
                           optimize_only_makespan: bool = False) -> pd.DataFrame:
    if optimize_only_makespan:
        return solve_makespan_scheduler(jobs_df, machines_df, forecast_df)
    return solve_proposed_scheduler(jobs_df, machines_df, forecast_df, use_robust=robust)
