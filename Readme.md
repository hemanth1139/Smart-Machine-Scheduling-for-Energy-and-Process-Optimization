# Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing

[![Submitted to Elsevier](https://img.shields.io/badge/Status-Submitted%20to%20Elsevier-blue.svg)](https://elsevier.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![OR-Tools](https://img.shields.io/badge/Solver-OR--Tools%20CP--SAT-4285F4.svg)](https://developers.google.com/optimization)

Official codebase accompanying the paper:  
**"Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing"**  
*Suresh Kumar S, Savitri R, Hemanth Kumar D, Balaji R, Bijlesh S*  
Department of Artificial Intelligence and Data Science, Rajalakshmi Engineering College, Chennai, India.  
*(Submitted to Elsevier)*

---

## 📌 Executive Summary

Modern industrial facilities operating under Time-of-Use (ToU) electricity tariffs and peak-demand penalties require scheduling strategies that balance operational deadlines with energy expenditure. This repository implements a complete **Predict-then-Optimize Framework** that integrates multi-quantile probabilistic energy forecasting with constraint-programming refinement for flexible job-shop scheduling.

### Key Performance Highlights (20-Seed Benchmark Evaluation)

| Metric | FCFS Baseline | FD-PDTS Robust | **Hybrid CP-SAT (Warm-Start)** | Improvement vs FCFS |
|---|---|---|---|---|
| **Total Energy Cost (INR)** | ₹187,371.53 ± 5,607.45 | ₹169,397.15 ± 6,877.50 | **₹127,254.28 ± 5,309.53** | **32.1% Savings** 💰 |
| **Peak Grid Load (kW)** | 784.48 kW | 780.73 kW | **491.58 ± 33.16 kW** | **37.3% Reduction** ⚡ |
| **Carbon Emissions (tCO₂)** | 735.87 ± 32.70 tCO₂ | 686.43 ± 40.83 tCO₂ | **558.80 ± 35.00 tCO₂** | **24.1% Reduction** 🌱 |
| **Power Factor Penalty (INR)**| ₹30,660.46 | ₹27,323.97 | **₹20,431.24** | **33.4% Reduction** 📈 |
| **On-Time Completion (%)** | 100.0% | 100.0% | **100.0%** | **0 Late Jobs** ✅ |

---

## 🏗️ System Architecture & Workflow

The end-to-end framework consists of four coupled modules:

```
┌───────────────────────────┐     ┌────────────────────────────────┐     ┌───────────────────────────────────┐
│ Industrial SCADA Dataset  │ ──► │ Feature Engineering Module     │ ──► │ Multi-Quantile XGBoost Engine     │
│ (35,040 15-min intervals) │     │ (Lag_1..96, Rolling Stats)     │     │ (p10/p50/p90, Non-Crossing Rearr.)│
└───────────────────────────┘     └────────────────────────────────┘     └───────────────────────────────────┘
                                                                                           │
┌───────────────────────────┐     ┌────────────────────────────────┐                       ▼
│ Interactive Dashboard UI  │ ◄── │ 12-Metric KPI Calculator Engine│ ◄── ┌───────────────────────────────────┐
│ (FastAPI + Glassmorphic) │     │ (Cost, Peak, CO2, PF Penalty)  │     │ 10-Algorithm Dispatching Engine   │
└───────────────────────────┘     └────────────────────────────────┘     │ (FD-PDTS + OR-Tools CP-SAT)       │
                                                                         └───────────────────────────────────┘
```

1. **Preprocessing & Feature Engineering**: Processes 1 year (35,040 records) of SCADA industry energy data. Extracts temporal features (NSM, day-of-week, week-status), multi-step lag features ($t-1, t-2, t-4, t-96$), and rolling window statistics ($4, 96$ slots).
2. **Quantile XGBoost Forecasting**: 7 independent quantile regressors ($p_{10}, p_{50}, p_{90}$ for active energy and CO₂, $p_{50}$ for power factor) trained with native `reg:quantileerror` and tariff sample weights ($3.0\times$ Peak, $1.5\times$ Medium, $1.0\times$ Off-Peak). Observation-level monotone rearrangement enforces $p_{10} \le p_{50} \le p_{90}$ (0.0% crossing rate). Recursive 48-hour forecasting updates all lag and rolling columns dynamically.
3. **10-Algorithm Dispatching & Refinement Engine**: Includes rule-based baselines, tariff-aware heuristics (FD-PDTS), and exact warm-started CP-SAT constraint programming.
4. **12-Metric KPI & Interactive Dashboard**: Serves JSON APIs via FastAPI and visualizes schedules, Gantt charts, forecasts, and comparative benchmarks through a dynamic dark-mode single-page frontend.

---

## ⚙️ Implemented Scheduling Algorithms

The benchmark suite evaluates **10 distinct scheduling strategies**:

| Algorithm | Type | Description |
|---|---|---|
| **FCFS** | Baseline | First-Come-First-Served; tariff-unaware arrival order placement. |
| **SPT** | Baseline | Shortest Processing Time first. |
| **LPT** | Baseline | Longest Processing Time first. |
| **EDD** | Baseline | Earliest Due Date first. |
| **Energy-Unaware Greedy** | Baseline | Arrival order placement prioritizing highest active power machines (worst-case allocation). |
| **Makespan Greedy** | Baseline | Speed-oriented load-balancing greedy minimizing machine completion time. |
| **FD-PDTS Deterministic** | Proposed Heuristic | Forecast-Driven Priority Dispatching with Tariff Shifting using $p_{50}$ forecasts & soft peak guards. |
| **FD-PDTS Robust** | Proposed Heuristic | Robust FD-PDTS variant applying a $1.25\times$ multiplier on $p_{90}$ tariff projections & overload risk. |
| **CP-SAT Warm-Start (Hybrid)** | Proposed Hybrid | OR-Tools CP-SAT solver initialized with FD-PDTS warm-start solution (120s limit). |
| **CP-SAT Cold-Start** | Ablation Study | OR-Tools CP-SAT solver executed without warm-start hints (proves warm-start necessity). |

---

## 🛠️ Verification & Quality Assurance (v2 Enhancements)

All preliminary prototype defects identified during initial testing have been fully resolved:

- ✅ **Recursive Multi-Step Forecasting**: Updated multi-step autoregressive rollouts to recompute all lag ($t-1, t-2, t-4, t-96$) and rolling mean/std features at every forecast interval.
- ✅ **Quantile Monotone Rearrangement**: Integrated post-hoc observation-level sorting (`_apply_non_crossing`), eliminating quantile crossing violations (reduced from 22.6% to **0.00%**).
- ✅ **Power Factor Bounding & Rescaling**: Standardized power factor training to $[0, 1]$ decimal space and inverse-transformed to percent ($0-100\%$) for dashboard reporting.
- ✅ **Peak-Load Unit Rectification**: Standardized kW power vs. kWh energy interval scaling ($P = E / 0.25\,\text{h}$) across all KPI evaluation steps.
- ✅ **Algorithmic Differentiation**: Differentiated Makespan Greedy (earliest-completion load balancing) from FCFS and FD-PDTS Robust ($1.25\times$ risk multiplier) from Deterministic.
- ✅ **20-Seed Empirical Validation**: Evaluated all 10 algorithms across 20 independent synthetic benchmark seeds (42–61) with 95% Confidence Intervals reported.

---

## 📂 Repository Structure

```
Smart-Machine-Scheduling-for-Energy-and-Process-Optimization/
├── backend/
│   ├── config.py              # Centralized configuration (tariffs, solver limits, seeds)
│   ├── preprocessing.py       # Data cleaning, cyclical encoding, lag/rolling feature engineering
│   ├── forecasting.py         # Multi-quantile XGBoost, rearrangement sort, recursive forecast
│   ├── generate_dataset.py    # Multi-seed synthetic job/machine instance generator
│   ├── scheduler.py           # 10 scheduling algorithms (FCFS, FD-PDTS, CP-SAT Warm/Cold)
│   ├── kpi_calculator.py      # 12-metric KPI calculation engine
│   ├── api.py                 # FastAPI REST backend
│   ├── run_pipeline.py        # Pipeline orchestrator (multi-seed, sensitivity, aggregate stats)
│   ├── requirements.txt       # Backend Python dependencies
│   ├── render.yaml            # Render backend deployment config
│   ├── data/                  # Industrial SCADA raw data & processed output
│   ├── models/                # Trained XGBoost models & scaler joblib binaries
│   └── output/                # Benchmark CSV results, multi-seed stats, solver logs
├── frontend/
│   ├── index.html             # Glassmorphic single-page dashboard HTML
│   ├── style.css              # Custom dark-theme glassmorphism CSS
│   ├── app.js                 # Dynamic UI logic, Chart.js & Gantt renderings
│   └── vercel.json            # Vercel frontend deployment config
└── Readme.md                  # Project documentation
```

---

## 📊 Empirical Results (20-Seed Benchmark Summary)

Summary of aggregate metrics across 20 independent synthetic scheduling instances (seeds 42–61):

```
Algorithm              Energy Cost (INR)        Peak Load (kW)   Carbon (tCO2)    On-Time (%)
---------------------------------------------------------------------------------------------
FCFS                   187,371.53 ± 5,607.45     784.48 ± 0.00    735.87 ± 32.70   100.0%
Energy_Unaware_Greedy  191,935.57 ± 5,687.44     784.48 ± 0.00    768.07 ± 35.66   100.0%
Makespan_Greedy        187,168.68 ± 5,940.02     784.48 ± 0.00    736.69 ± 34.21   100.0%
SPT                    171,576.08 ± 4,278.27     762.53 ± 15.57   799.50 ± 34.94    98.6%
EDD                    183,513.60 ± 5,814.67     782.73 ± 3.66    758.66 ± 33.45   100.0%
FD_PDTS_Deterministic  169,841.13 ± 6,606.72     780.73 ± 7.85    683.86 ± 39.06   100.0%
FD_PDTS_Robust         169,397.15 ± 6,877.50     780.73 ± 7.85    686.43 ± 40.83   100.0%
CP_SAT_Warm (Hybrid)   127,254.28 ± 5,309.53     491.58 ± 33.16   558.80 ± 35.00   100.0%
CP_SAT_Cold            88,827.30  ± 4,804.01     153.43 ± 22.16   672.47 ± 35.69    93.2%
```

> 💡 **Note on CP-SAT Cold-Start**: While CP-SAT Cold achieves low energy costs, it fails on-time completion constraints (averaging 12.25 late jobs and 445 minutes of waiting time per instance). Warm-starting CP-SAT with FD-PDTS guarantees 100% on-time delivery while achieving **32.1% cost savings** and **37.3% peak load reduction**.

---

## 🚀 Quick Start & Installation

### 1. Prerequisites & Environment Setup

Ensure Python 3.10+ is installed:

```bash
git clone https://github.com/hemanth1139/Smart-Machine-Scheduling-for-Energy-and-Process-Optimization.git
cd Smart-Machine-Scheduling-for-Energy-and-Process-Optimization
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Execution Pipeline

To run the complete preprocessing, model training, multi-seed benchmark execution, and sensitivity analysis:

```bash
python backend/run_pipeline.py
```

### 3. Launching the API & Interactive Dashboard

To start the FastAPI REST backend server:

```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

Access the interactive web dashboard by opening `frontend/index.html` in any modern web browser or navigating to `http://localhost:8000/app/`.

---

## 📄 Citation

If you reference or build upon this work in your research, please cite our paper:

```bibtex
@article{kumar2026forecastdriven,
  title     = {Forecast-Driven Energy-Aware Scheduling for Smart Manufacturing},
  author    = {Kumar S, Suresh and R, Savitri and Kumar D, Hemanth and R, Balaji and S, Bijlesh},
  journal   = {Submitted to Elsevier},
  year      = {2026}
}
```

---

## 📧 Contact & Support

For inquiries regarding dataset access, codebase reproduction, or technical details, please reach out to the Department of Artificial Intelligence and Data Science, Rajalakshmi Engineering College, Chennai, India.
