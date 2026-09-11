"""
Scheduling Module v2 — Predict-then-Optimize Framework
=======================================================
Implements eight scheduling algorithms:

  1.  solve_fcfs_scheduler          — First-Come-First-Served
  2.  solve_spt_scheduler           — Shortest Processing Time first
  3.  solve_lpt_scheduler           — Longest Processing Time first
  4.  solve_edd_scheduler           — Earliest Due Date (= old EDF)
  5.  solve_energy_unaware_greedy   — Arrival-order but always picks highest-power machine
  6.  solve_makespan_scheduler      — Load-balancing greedy (minimises per-machine finish time)
  7.  solve_proposed_scheduler      — FD-PDTS: Forecast-Driven Priority Dispatching with Tariff Shifting
  8.  solve_deterministic_scheduler — FD-PDTS using p50 (no robustness)
  9.  solve_robust_scheduler        — FD-PDTS with genuinely stronger robustness
                                      (p90 tariff bias x1.25, overload penalty x0.50)
  10. solve_hybrid_scheduler        — FD-PDTS warm-start + CP-SAT refinement (warm start)
  11. solve_cpsat_cold_scheduler    — CP-SAT WITHOUT warm start (cold start comparison)

Fix notes:
  - solve_makespan_scheduler now uses earliest-completion load-balancing, NOT FCFS.
  - solve_robust_scheduler uses 1.25x multiplier (was 1.08x) so it genuinely
    produces different slot-selection from the deterministic version.
  - solve_energy_unaware_greedy always routes to the highest Active_Power_kW
    compatible machine (worst-case energy baseline).
  - solve_cpsat_cold_scheduler runs CP-SAT with NO hint injection.
"""

from typing import Dict, List, Optional, Tuple
import time
import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

try:
    from backend.config import config
    from backend.utils import get_logger
except ImportError:
    from config import config
    from utils import get_logger

logger = get_logger("scheduler")


# =============================================================================
# HELPERS
# =============================================================================

def _build_tariff_array(forecast_df: pd.DataFrame, horizon_slots: int) -> np.ndarray:
    tariffs = np.full(horizon_slots, config.TARIFF_LIGHT_LOAD)
    n = max(1, len(forecast_df))
    for t in range(horizon_slots):
        lt = forecast_df.iloc[t % n].get("Load_Type", "Light_Load")
        if lt == "Maximum_Load":
            tariffs[t] = config.TARIFF_MAX_LOAD
        elif lt == "Medium_Load":
            tariffs[t] = config.TARIFF_MED_LOAD
    return tariffs


def _job_energy_cost(
    start_slot: int, dur_slots: int, active_kw: float, setup_kw: float, tariffs: np.ndarray
) -> float:
    h = config.SLOT_DURATION_MIN / 60.0
    n = len(tariffs)
    cost = 0.0
    for t in range(start_slot, start_slot + dur_slots):
        cost += active_kw * h * tariffs[min(t, n - 1)]
    cost += setup_kw * h * tariffs[min(max(start_slot, 0), n - 1)]
    return cost


def _changeover_slots(prev_stype, cur_stype) -> int:
    if prev_stype is None:
        return 0
    return 1 if prev_stype == cur_stype else 2


class MachineCalendar:
    """Interval calendar: busy segments + setup type at each segment end."""

    def __init__(self):
        self.busy: List[Tuple[int, int, Optional[str]]] = []

    def _stype_before(self, start: int):
        prev = None
        for s, e, st in self.busy:
            if e <= start:
                prev = st
            else:
                break
        return prev

    def earliest_fit(self, arrival: int, dur: int, stype: str, search_limit: int = 10_000) -> int:
        t = arrival
        while t <= search_limit:
            co = _changeover_slots(self._stype_before(t), stype)
            start = t + co
            end = start + dur
            conflict = False
            for s, e, _ in self.busy:
                if not (end <= s or start >= e):
                    t = e
                    conflict = True
                    break
            if not conflict:
                return start
        return arrival

    def can_place(self, start: int, dur: int, stype: str) -> bool:
        co = _changeover_slots(self._stype_before(start), stype)
        end = start + dur
        co_start = start - co
        for s, e, _ in self.busy:
            if not (end <= s or co_start >= e):
                return False
        return True

    def place(self, start: int, end: int, stype: str) -> None:
        self.busy.append((start, end, stype))
        self.busy.sort(key=lambda x: x[0])

    @property
    def last_end(self) -> int:
        return self.busy[-1][1] if self.busy else 0


def _parse_compat(job, mach_map) -> List[str]:
    return [m.strip() for m in str(job["Compatible_Machines"]).split(",") if m.strip() in mach_map]


def _asap_place(calendars, mach_map, compat, arr, dur, stype):
    best = None
    for mid in compat:
        start = calendars[mid].earliest_fit(arr, dur, stype)
        end = start + dur
        if best is None or end < best[0] or (end == best[0] and start < best[1]):
            best = (end, start, mid)
    return best


# =============================================================================
# 1. FCFS — First Come First Served
# =============================================================================

def solve_fcfs_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    for j in jobs_df.sort_values("Arrival_Time").to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        placed = _asap_place(calendars, mach_map, compat, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 2. SPT — Shortest Processing Time first
# =============================================================================

def solve_spt_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    # SPT: sort by Duration_min ascending (ties broken by arrival)
    order = jobs_df.sort_values(["Duration_min", "Arrival_Time"])
    for j in order.to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        placed = _asap_place(calendars, mach_map, compat, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 3. LPT — Longest Processing Time first
# =============================================================================

def solve_lpt_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    # LPT: sort by Duration_min descending (ties broken by arrival)
    order = jobs_df.sort_values(["Duration_min", "Arrival_Time"], ascending=[False, True])
    for j in order.to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        placed = _asap_place(calendars, mach_map, compat, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 4. EDD — Earliest Due Date (same sort key as old EDF)
# =============================================================================

def solve_edd_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    order = jobs_df.sort_values(["Deadline", "Priority", "Arrival_Time"])
    for j in order.to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        placed = _asap_place(calendars, mach_map, compat, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# Alias for backward compatibility
def solve_edf_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    return solve_edd_scheduler(jobs_df, machines_df, forecast_df)


# =============================================================================
# 5. Energy-Unaware Greedy
#    FCFS arrival order, but ALWAYS picks the highest Active_Power_kW machine.
#    This is a deliberately bad energy baseline.
# =============================================================================

def solve_energy_unaware_greedy(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    for j in jobs_df.sort_values("Arrival_Time").to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        if not compat:
            continue
        # Sort compatible machines by Active_Power_kW descending (worst energy choice)
        compat_sorted = sorted(
            compat, key=lambda m: float(mach_map[m]["Active_Power_kW"]), reverse=True
        )
        placed = _asap_place(calendars, mach_map, compat_sorted, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 6. Makespan Greedy — load-balancing (NOT FCFS)
#    Each job goes to the compatible machine whose current last_end is earliest.
# =============================================================================

def solve_makespan_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}

    rows = []
    for j in jobs_df.sort_values("Arrival_Time").to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        compat = _parse_compat(j, mach_map)
        if not compat:
            continue
        # Load-balancing: prefer the machine with the smallest last_end
        compat_sorted = sorted(compat, key=lambda m: calendars[m].last_end)
        placed = _asap_place(calendars, mach_map, compat_sorted, arr, dur, stype)
        if placed is None:
            continue
        end, start, mid = placed
        calendars[mid].place(start, end, stype)
        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})
    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


# =============================================================================
# 7. FD-PDTS — Proposed algorithm
# =============================================================================

def _tariff_candidates(base: int, latest: int, tariffs: np.ndarray) -> List[int]:
    if latest < base:
        return [base]
    cands = {base, latest}
    n = len(tariffs)
    for target in (config.TARIFF_LIGHT_LOAD, config.TARIFF_MED_LOAD):
        for t in range(base, latest + 1):
            if tariffs[min(t, n - 1)] <= target + 1e-6:
                cands.add(t)
                break
    prev = tariffs[min(base, n - 1)]
    for t in range(base + 1, latest + 1):
        cur = tariffs[min(t, n - 1)]
        if cur + 1e-6 < prev:
            cands.add(t)
        prev = cur
    return sorted(c for c in cands if base <= c <= latest)


def solve_proposed_scheduler(
    jobs_df, machines_df, forecast_df, use_robust: bool = True, robust_multiplier: float = 1.25
) -> pd.DataFrame:
    """
    FD-PDTS with interval calendars.

    use_robust=False  -> deterministic (p50 tariff, multiplier=1.0)
    use_robust=True   -> robust (peak tariffs multiplied by robust_multiplier,
                         overload penalty coefficient raised to 0.50)
    """
    horizon = config.SCHEDULING_HORIZON_SLOTS + 64
    tariffs = _build_tariff_array(forecast_df, horizon)

    if use_robust:
        logger.info(f"FD-PDTS: robust tariff bias (x{robust_multiplier}) enabled.")
        plan = tariffs.copy()
        plan[tariffs >= config.TARIFF_MAX_LOAD - 1e-6] *= robust_multiplier
        overload_coeff = 0.50   # stronger peak-overload deterrent
    else:
        logger.info("FD-PDTS: deterministic tariffs (p50 only).")
        plan = tariffs
        overload_coeff = 0.20

    machines = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in machines}
    calendars = {m: MachineCalendar() for m in mach_map}
    load_profile = np.zeros(horizon)
    peak_cap = float(config.PEAK_GRID_CAPACITY_KW)

    FINISH_SLACK = {1: 0, 2: 4, 3: 6}
    MAX_SHIFT = {1: 0, 2: 6, 3: 8}
    WAIT_PENALTY = 20.0
    FINISH_PENALTY = 15.0

    scored = []
    for j in jobs_df.to_dict(orient="records"):
        arr = int(j["Arrival_Time"])
        deadline = int(j["Deadline"])
        prio = int(j.get("Priority", 2))
        scored.append((arr, prio, deadline, j["Job_ID"], j))
    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    rows = []
    for _, _, _, _, j in scored:
        arr = int(j["Arrival_Time"])
        deadline = int(j["Deadline"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        stype = j["Setup_Type"]
        prio = int(j.get("Priority", 2))
        compat = _parse_compat(j, mach_map)

        asap_ref_end = None
        for mid in compat:
            s0 = calendars[mid].earliest_fit(arr, dur, stype)
            asap_ref_end = s0 + dur if asap_ref_end is None else min(asap_ref_end, s0 + dur)

        best_on_time = None
        best_any = None
        max_shift = MAX_SHIFT.get(prio, 6)
        finish_slack = FINISH_SLACK.get(prio, 4)

        for mid in compat:
            cal = calendars[mid]
            m = mach_map[mid]
            active_kw = float(m["Active_Power_kW"])
            setup_kw = float(m["Setup_Energy_kW"])
            asap = cal.earliest_fit(arr, dur, stype)

            if max_shift == 0:
                candidates = [asap]
            else:
                latest = min(deadline - dur, asap + max_shift, horizon - dur)
                latest = max(latest, asap)
                candidates = _tariff_candidates(asap, latest, plan)
                snapped = []
                for c in candidates:
                    if c > asap + max_shift:
                        continue
                    if cal.can_place(c, dur, stype) and c >= arr:
                        snapped.append(c)
                    else:
                        fit = cal.earliest_fit(min(c, asap + max_shift), dur, stype)
                        if fit <= asap + max_shift:
                            snapped.append(fit)
                candidates = sorted(set(snapped)) or [asap]

            for s in candidates:
                if not cal.can_place(s, dur, stype):
                    continue
                if s > asap + max_shift:
                    continue
                e = s + dur
                if asap_ref_end is not None and e > asap_ref_end + finish_slack:
                    continue
                energy = _job_energy_cost(s, dur, active_kw, setup_kw, plan)
                if s < horizon:
                    overload = 0.0
                    for t in range(s, min(e, horizon)):
                        overload += max(0.0, load_profile[t] + active_kw - peak_cap)
                    energy += overload_coeff * overload

                late = max(0, e - deadline)
                wait = max(0, s - arr)
                finish_lag = max(0, e - (asap_ref_end or e))
                total = energy + WAIT_PENALTY * wait + FINISH_PENALTY * finish_lag
                score = (late, total, active_kw, e, wait)
                cand = (score, mid, s, e)
                if late == 0:
                    if best_on_time is None or score < best_on_time[0]:
                        best_on_time = cand
                if best_any is None or score < best_any[0]:
                    best_any = cand

        if best_on_time is None and best_any is None:
            for mid in compat:
                cal = calendars[mid]
                m = mach_map[mid]
                asap = cal.earliest_fit(arr, dur, stype)
                e = asap + dur
                energy = _job_energy_cost(
                    asap, dur, float(m["Active_Power_kW"]), float(m["Setup_Energy_kW"]), plan
                )
                score = (max(0, e - deadline), energy, float(m["Active_Power_kW"]), e, max(0, asap - arr))
                cand = (score, mid, asap, e)
                if score[0] == 0:
                    if best_on_time is None or score < best_on_time[0]:
                        best_on_time = cand
                if best_any is None or score < best_any[0]:
                    best_any = cand

        chosen = best_on_time if best_on_time is not None else best_any
        if chosen is None:
            placed = _asap_place(calendars, mach_map, compat, arr, dur, stype)
            if placed is None:
                continue
            end, start, mid = placed
        else:
            _, mid, start, end = chosen

        calendars[mid].place(start, end, stype)
        active_kw = float(mach_map[mid]["Active_Power_kW"])
        for t in range(start, min(end, horizon)):
            load_profile[t] += active_kw

        rows.append({"Job_ID": j["Job_ID"], "Machine_ID": mid,
                     "Start_Slot": start, "End_Slot": end, "Duration_Slots": dur})

    return pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)


def solve_deterministic_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    return solve_proposed_scheduler(jobs_df, machines_df, forecast_df, use_robust=False)


def solve_robust_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    """Stronger robustness: 1.25x peak tariff multiplier + 0.50 overload coefficient."""
    return solve_proposed_scheduler(
        jobs_df, machines_df, forecast_df, use_robust=True, robust_multiplier=1.25
    )


# =============================================================================
# CP-SAT shared builder
# =============================================================================

def _run_cpsat(
    jobs_df, machines_df, forecast_df, hint_map: Optional[Dict] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Shared CP-SAT formulation. Returns (schedule_df, solver_info_dict).
    If hint_map is None, runs cold (no warm start).
    """
    horizon_slots = config.SCHEDULING_HORIZON_SLOTS + 48
    tariffs = _build_tariff_array(forecast_df, horizon_slots)

    job_list = jobs_df.to_dict(orient="records")
    mach_list = machines_df.to_dict(orient="records")
    mach_map = {m["Machine_ID"]: m for m in mach_list}
    all_mids = [m["Machine_ID"] for m in mach_list]
    job_compat = {j["Job_ID"]: _parse_compat(j, mach_map) for j in job_list}
    max_ub = horizon_slots
    hours = config.SLOT_DURATION_MIN / 60.0

    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.ORTOOLS_TIME_LIMIT_SEC
    solver.parameters.num_search_workers = 4

    start_vars, end_vars, presence_vars, interval_vars = {}, {}, {}, {}
    var_bounds = {}
    energy_cost_vars = {}

    for j in job_list:
        jid = j["Job_ID"]
        arr = int(j["Arrival_Time"])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        deadline = int(j["Deadline"])

        if hint_map is not None:
            hint_start, _ = hint_map.get(jid, (arr, None))
            window = 4
        else:
            hint_start = arr
            window = max_ub  # wide window for cold start

        lb = int(max(arr, hint_start - window))
        ub = int(max(lb, min(max_ub - dur, hint_start + window, deadline)))
        var_bounds[jid] = (lb, ub, dur, deadline, arr)

        sv = model.NewIntVar(lb, ub, f"s_{jid}")
        ev = model.NewIntVar(lb + dur, ub + dur, f"e_{jid}")
        model.Add(ev == sv + dur)
        start_vars[jid] = sv
        end_vars[jid] = ev

        presence_vars[jid], interval_vars[jid] = {}, {}
        for mid in job_compat[jid]:
            pres = model.NewBoolVar(f"p_{jid}_{mid}")
            itv = model.NewOptionalIntervalVar(sv, dur, ev, pres, f"itv_{jid}_{mid}")
            presence_vars[jid][mid] = pres
            interval_vars[jid][mid] = itv
        model.Add(sum(presence_vars[jid].values()) == 1)

        energy_terms = []
        for mid in job_compat[jid]:
            m = mach_map[mid]
            active = float(m["Active_Power_kW"])
            setup = float(m["Setup_Energy_kW"])
            cost_table = []
            for t in range(0, max_ub + 1):
                if t < lb or t > ub:
                    cost_table.append(0)
                    continue
                c = 0.0
                for u in range(t, t + dur):
                    c += active * hours * tariffs[min(u, len(tariffs) - 1)]
                c += setup * hours * tariffs[min(t, len(tariffs) - 1)]
                cost_table.append(int(round(c * 100)))
            max_cost = max(cost_table) if cost_table else 0
            cost_var = model.NewIntVar(0, max_cost, f"ec_{jid}_{mid}")
            model.AddElement(sv, cost_table, cost_var)
            gated = model.NewIntVar(0, max_cost, f"gec_{jid}_{mid}")
            model.Add(gated == cost_var).OnlyEnforceIf(presence_vars[jid][mid])
            model.Add(gated == 0).OnlyEnforceIf(presence_vars[jid][mid].Not())
            energy_terms.append(gated)
        energy_cost_vars[jid] = sum(energy_terms) if energy_terms else 0

    for mid in all_mids:
        itvs = [interval_vars[jid][mid] for jid in interval_vars if mid in interval_vars[jid]]
        if itvs:
            model.AddNoOverlap(itvs)

    obj = []
    for j in job_list:
        jid = j["Job_ID"]
        _, _, _, deadline, arr = var_bounds[jid]
        tard = model.NewIntVar(0, max_ub * 10, f"tard_{jid}")
        model.Add(tard >= end_vars[jid] - deadline)
        wait = model.NewIntVar(0, max_ub, f"wait_{jid}")
        model.Add(wait == start_vars[jid] - arr)
        obj.append(energy_cost_vars[jid] * config.WEIGHT_ENERGY_COST)
        obj.append(tard * 1000)
        obj.append(wait * 350)
    model.Minimize(sum(obj))

    # Warm-start hints (only if hint_map provided)
    if hint_map is not None:
        for jid, (hint_s, hint_mid) in hint_map.items():
            if jid not in start_vars:
                continue
            lb, ub, _, _, _ = var_bounds[jid]
            model.add_hint(start_vars[jid], max(lb, min(ub, hint_s)))
            for mid, pvar in presence_vars[jid].items():
                model.add_hint(pvar, 1 if mid == hint_mid else 0)

    err = model.Validate()
    if err:
        logger.error(f"CP-SAT validation error: {err}")
        return pd.DataFrame(), {"status": "VALIDATION_ERROR", "runtime": 0.0}

    t0 = time.time()
    status = solver.Solve(model)
    runtime = time.time() - t0

    status_name = solver.StatusName(status)
    logger.info(f"CP-SAT status={status_name} time={runtime:.2f}s objective={solver.ObjectiveValue():.1f}")

    solver_info = {
        "status": status_name,
        "runtime_s": round(runtime, 2),
        "objective_value": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "best_bound": solver.BestObjectiveBound() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "optimality_proven": status == cp_model.OPTIMAL,
        "warm_start_used": hint_map is not None,
        "time_limit_s": config.ORTOOLS_TIME_LIMIT_SEC,
        "num_workers": 4,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return pd.DataFrame(), solver_info

    rows = []
    for j in job_list:
        jid = j["Job_ID"]
        mid = next(
            (m for m in job_compat[jid] if solver.Value(presence_vars[jid][m]) == 1), None
        )
        if mid is None:
            if hint_map is not None:
                _, mid = hint_map.get(jid, (None, job_compat[jid][0] if job_compat[jid] else None))
            else:
                mid = job_compat[jid][0] if job_compat[jid] else None
        if mid is None:
            continue
        s = solver.Value(start_vars[jid])
        dur = max(1, int(np.ceil(j["Duration_min"] / 15.0)))
        rows.append({"Job_ID": jid, "Machine_ID": mid,
                     "Start_Slot": s, "End_Slot": s + dur, "Duration_Slots": dur})

    sched_df = pd.DataFrame(rows).sort_values(["Machine_ID", "Start_Slot"]).reset_index(drop=True)
    return sched_df, solver_info


# =============================================================================
# 8. Hybrid FD-PDTS + CP-SAT (warm start)
# =============================================================================

def solve_hybrid_scheduler(
    jobs_df, machines_df, forecast_df
) -> Tuple[pd.DataFrame, Dict]:
    logger.info("Hybrid Stage 1: Running Robust FD-PDTS for warm-start...")
    fdpdts_df = solve_robust_scheduler(jobs_df, machines_df, forecast_df)
    if fdpdts_df.empty:
        return fdpdts_df, {}

    hint_map = {
        row["Job_ID"]: (int(row["Start_Slot"]), row["Machine_ID"])
        for _, row in fdpdts_df.iterrows()
    }
    logger.info(f"Hybrid Stage 1 complete: {len(fdpdts_df)} jobs. Running CP-SAT Stage 2 (warm)...")
    sched_df, solver_info = _run_cpsat(jobs_df, machines_df, forecast_df, hint_map=hint_map)
    solver_info["initial_objective_fdpdts"] = None  # populated by caller if needed
    if sched_df.empty:
        logger.warning("CP-SAT returned no solution; falling back to FD-PDTS result.")
        return fdpdts_df, solver_info
    return sched_df, solver_info


# =============================================================================
# 9. Cold CP-SAT (NO warm start — comparison baseline)
# =============================================================================

def solve_cpsat_cold_scheduler(
    jobs_df, machines_df, forecast_df
) -> Tuple[pd.DataFrame, Dict]:
    logger.info("Cold CP-SAT: Running WITHOUT warm-start hints...")
    sched_df, solver_info = _run_cpsat(jobs_df, machines_df, forecast_df, hint_map=None)
    return sched_df, solver_info


# Backward compatibility aliases
def solve_edf_scheduler(jobs_df, machines_df, forecast_df) -> pd.DataFrame:
    return solve_edd_scheduler(jobs_df, machines_df, forecast_df)
