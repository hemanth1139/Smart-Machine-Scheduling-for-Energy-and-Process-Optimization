# Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing

A predict-then-optimize framework that combines probabilistic energy forecasting with production scheduling and constraint-programming refinement for smart manufacturing facilities exposed to time-of-use electricity pricing and peak-demand charges.

This repository accompanies the paper *"Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing"* (Suresh Kumar S, Savithri R, Hemanth Kumar D, Balaji R, Bijlesh S — Department of Artificial Intelligence and Data Science, Rajalakshmi Engineering College, Chennai, India).

---

## ⚠️ Known Issues (read before using)

This is a **prototype research implementation**, not validated industrial software. An internal audit identified the following unresolved defects. Results produced by the current code should be treated as preliminary until these are fixed.

1. **Recursive forecast is incomplete.** The 48-hour recursive forecast only updates the one-step lag feature. Longer lags, rolling statistics, and the exponentially weighted moving average remain fixed instead of being recomputed from prior predictions. Long-horizon forecasts are not currently reliable.
2. **Quantile calibration is off.** Independently trained quantile models (p10/p50/p90) produce crossing intervals (i.e., violate p10 ≤ p50 ≤ p90) in ~13% of test rows, and empirical coverage is far from nominal (p10 coverage ≈ 99.99%, p90 coverage ≈ 48.46%). A monotone rearrangement correction (Chernozhukov et al., 2010) is planned but not yet implemented.
3. **Power-factor model output is unbounded.** The power-factor model currently produces a constant value outside the physically valid range of [0, 1]. The target representation / output layer needs correction.
4. **Peak-load KPI has a unit bug.** The peak-load KPI currently mixes kWh energy values with kW power values without applying the required 15-minute interval conversion (P = E / 0.25 h). Reported peak-load figures should be recomputed with this fix before being cited.
5. **Two baselines are not yet differentiated.** In the current benchmark, the Makespan Greedy baseline is numerically identical to FCFS, and the deterministic vs. robust FD-PDTS variants produce identical results. This indicates a bug in strategy differentiation rather than a real finding.
6. **Single benchmark instance.** All reported results come from one synthetic benchmark (180 jobs, 8 machines). No confidence intervals, repeated trials, or varied random seeds have been run yet.

See the paper's *Validity Assessment* and *Future Work* sections for full details and the planned correction roadmap. Contributions/PRs addressing any of the above are welcome.

---

## Overview

The pipeline connects four stages:

```
Industrial energy data ─┐
                         ├─► Preprocessing & features ─► Quantile XGBoost ─┐
Synthetic job/machine ───┘                                                 ├─► Scheduling engine ─► KPI calculator ─► Streamlit dashboard
                                                                            │   (FCFS, EDF, FD-PDTS,
                                                                            │    FD-PDTS Robust, Makespan
                                                                            │    Greedy, Hybrid CP-SAT)
```

**Forecasting:** Tariff-weighted quantile XGBoost models predict p10/p50/p90 active energy and carbon emissions, plus a p50 power-factor estimate — 7 models trained independently, with higher pinball-loss weights assigned to maximum-load periods.

**Scheduling:** Six strategies are implemented and compared:
- **FCFS** — first-come-first-served, tariff-unaware baseline
- **EDF** — earliest-deadline-first, deadline-aware but tariff-unaware
- **FD-PDTS** — proposed tariff-aware heuristic; scores candidate placements using p50 forecasts, waiting time, tardiness, and a peak-load guard
- **FD-PDTS Robust** — uses the upper forecast band instead of p50 when scoring placements
- **Makespan Greedy** — speed-oriented baseline, earliest completion time
- **Hybrid CP-SAT** — FD-PDTS solution used as a warm start for an OR-Tools CP-SAT refinement stage

**Evaluation:** A 12-metric KPI layer covers economic (cost), operational (makespan, utilization, waiting time), compliance (on-time %, tardiness), environmental (CO₂), and quality (power-factor penalty) outcomes, surfaced through a Streamlit dashboard.

---

## Repository Structure

```
.
├── data/                  # Industrial energy dataset + synthetic job/machine generator
├── preprocessing/         # Feature engineering (cyclical encoding, lags, rolling stats)
├── forecasting/           # Quantile XGBoost training and inference
├── scheduling/            # FCFS, EDF, FD-PDTS, FD-PDTS Robust, Makespan Greedy, CP-SAT
├── kpi/                   # KPI computation layer
├── dashboard/             # Streamlit app
├── notebooks/             # Exploratory analysis / experiment notebooks
├── configs/                # Centralized config (seed, tariff levels, resolution, forecast settings)
└── README.md
```

*(Adjust this tree to match your actual folder layout before publishing.)*

---

## Dataset

| Item | Value |
|---|---|
| Energy records | 35,040 |
| Sampling interval | 15 min |
| Energy coverage | 1 year (2018) |
| Jobs | 180 |
| Machines | 8 |
| Average job duration | 62.75 min |
| Peak-hour arrivals | 75% |
| Compatible machines/job | 2–4 |
| Setup types | 3 |

The energy dataset includes active energy usage, reactive power, carbon information, power factor, weekday/weekend status, day-of-week, and load type. Data is split chronologically 60/20/20 (train/val/test) to avoid temporal leakage. Note: the benchmark's job arrival distribution (75% during peak tariff periods) is deliberately favorable to energy-aware scheduling — see Validity Assessment in the paper.

---

## Installation

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
pip install -r requirements.txt
```

*(Fill in actual dependencies — e.g., xgboost, ortools, streamlit, pandas, numpy, scikit-learn, joblib.)*

---

## Usage

```bash
# 1. Preprocess raw energy data and generate features
python preprocessing/run_preprocessing.py

# 2. Train quantile XGBoost forecasting models
python forecasting/train.py

# 3. Generate synthetic job/machine benchmark
python data/generate_synthetic_jobs.py

# 4. Run scheduling strategies and compute KPIs
python scheduling/run_benchmark.py

# 5. Launch the dashboard
streamlit run dashboard/app.py
```

*(Update commands/paths to match your actual scripts.)*

---

## Results (Preliminary)

On the single synthetic benchmark (180 jobs, 8 machines), the hybrid CP-SAT schedule reported reductions in energy cost and peak grid load relative to FCFS, at the cost of increased average waiting time. **These figures are affected by the known issues listed above (particularly #2 and #4) and should be treated as provisional pending correction.** See the paper's Evaluation and Validity Assessment sections for full numbers and caveats.

---

## Roadmap

- [ ] Fix recursive forecast to recompute all lag/rolling features at each step
- [ ] Apply monotone rearrangement to resolve quantile crossing
- [ ] Bound power-factor model output to [0, 1]
- [ ] Fix peak-load KPI unit conversion (kWh → kW)
- [ ] Differentiate Makespan Greedy from FCFS and FD-PDTS Robust from FD-PDTS
- [ ] Expand benchmark to multiple synthetic instances with varying job counts, machine fleets, deadline tightness, and tariff spread
- [ ] Report results with confidence intervals and fixed seeds
- [ ] Add SPT, EDD, CP-SAT-without-warm-start, MIP, and oracle baselines
- [ ] Incorporate carbon, peak-load, and power-factor terms directly into the CP-SAT objective

---

## Citation

If you use this code or build on this work, please cite:

```bibtex
@inproceedings{kumar2026forecastdriven,
  title     = {Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing},
  author    = {Suresh Kumar S , Savitri R , Hemanth Kumar D , Balaji R , Bijlesh S},
  booktitle = {arXiv preprint},
  year      = {2026}
}
```

*(Update once you have a final arXiv ID / venue.)*

---



For questions, issues, or collaboration, please open a GitHub issue or contact the authors via the Department of Artificial Intelligence and Data Science, Rajalakshmi Engineering College, Chennai, India.
