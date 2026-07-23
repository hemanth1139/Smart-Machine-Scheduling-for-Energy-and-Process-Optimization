# AI-Based Smart Machine Scheduling for Energy & Process Optimization

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Phase 1](https://img.shields.io/badge/Phase%201-Foundation%20%26%20Preprocessing-success.svg)]()
[![Phase 2](https://img.shields.io/badge/Phase%202-Energy%20Demand%20Forecasting-success.svg)]()
[![Phase 3](https://img.shields.io/badge/Phase%203-CP--SAT%20Machine%20Scheduling-success.svg)]()
[![Phase 4](https://img.shields.io/badge/Phase%204-Streamlit%20Interactive%20Dashboard-success.svg)]()
[![Phase 5](https://img.shields.io/badge/Phase%205-System%20Integration%20%26%20Testing-success.svg)]()
[![Build Status](https://img.shields.io/badge/Pytest-Passing-success.svg)]()

## 📌 Executive Summary

Industrial manufacturing facilities incur significant electricity costs when running energy-intensive machines during peak tariff hours. This project presents an end-to-end, production-ready **AI-Based Smart Machine Scheduling & Energy Optimization System**.

By combining **Time-Series Machine Learning (XGBoost Regressor)** to forecast 15-minute industrial power demand profiles with **Mathematical Constraint Programming (Google OR-Tools CP-SAT Solver)**, the system automatically schedules production jobs to compatible machines while avoiding peak-tariff electricity windows, reducing energy costs by over **25%** and shifting peak-hour electrical load.

---

## 🔄 End-to-End System Workflow

```
┌─────────────────────────┐
│   Raw Datasets Loading  │ (UCI Steel Energy, Jobs, Machines)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Data Quality Validation │ (Missingness, duplicates, domain bounds)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Data Cleaning & Impute  │ (Deduplication, forward-fill, typing)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Feature Engineering   │ (Lags 1..96, rolling mean/std, cyclical hour/month)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ XGBoost Demand Forecast │ (15-min resolution 24h energy load curve)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ CP-SAT Machine Solver   │ (Multi-objective energy cost & delay minimization)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ KPI Calculation & Report│ (Cost savings $, Peak reduction, On-time %)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Streamlit Web UI      │ (Multi-page interactive Plotly dashboard)
└─────────────────────────┘
```

---

## 📁 Repository Directory Structure

```
Smart-Machine-Scheduling-for-Energy-and-Process-Optimization/
│
├── config/                     # Centralized Configuration & Hyperparameters
│   ├── __init__.py
│   └── config.py               # Relative paths, XGBoost hyperparams, CP-SAT weights
│
├── data/                       # Datasets Storage
│   ├── raw/                    # Raw UCI Steel Energy, Job & Machine datasets
│   └── processed/              # Cleaned & feature-engineered CSV files
│
├── preprocessing/              # [Phase 1] Preprocessing Package
├── forecasting/                # [Phase 2] Energy Demand Forecasting Package
├── scheduler/                  # [Phase 3] Machine Scheduling Package
│
├── dashboard/                  # [Phase 4] Streamlit Interactive Web Application
│   ├── app.py                  # Streamlit multi-page entry point
│   ├── pages/                  # Home, Forecasting, Scheduling, Machine Analytics, KPI, Comparison, Reports, Settings
│   ├── components/             # Theme, Navbar, Sidebar, Cards, Metrics, Charts, Tables
│   └── utils/                  # Loader, Formatter, Exporter, Logger
│
├── tests/                      # [Phase 5] Automated Pytest Test Suite
│
├── models/                     # Serialized Model Artifacts (.joblib)
├── outputs/                    # Pipeline Artifact Outputs (forecasting/, scheduling/, reports/, charts/, eda/)
├── logs/                       # System Execution Logs (pipeline.log, dashboard.log)
├── temp/                       # Temporary scratch directory
├── main.py                     # Single unified CLI & pipeline entry point
├── main_phase2.py              # Phase 2 CLI runner
├── main_phase3.py              # Phase 3 CLI runner
├── main_phase4.py              # Phase 4 Dashboard launcher
├── requirements.txt            # Python dependencies
└── README.md                   # System documentation
```

---

## ⚡ Datasets Used

1. **UCI Steel Industry Energy Consumption Dataset**: 35,042 records logged at 15-minute intervals throughout 2018.
2. **Synthetic Job Specifications Table (`job_table.csv`)**: 500 production jobs (`Job_ID`, `Duration_min`, `Deadline`, `Priority`, `Compatible_Machines`, `Arrival_Time`).
3. **Synthetic Machine Specifications Table (`machine_table.csv`)**: 10 industrial machines (`Machine_ID`, `Idle_Power_kW`, `Active_Power_kW`, `Changeover_Time_min`, `Available_From`, `Available_To`).

---

## ⚙️ Quick Start & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Full Application (Recommended)
Run the main execution script. This automatically executes the full data $\rightarrow$ forecasting $\rightarrow$ scheduling pipeline and launches the Streamlit UI safely via Python:

```bash
python main.py
```

---

## 💻 CLI Usage Options

The unified entry point `main.py` supports modular command-line flags:

| Command | Description |
|---|---|
| `python main.py` | Runs complete end-to-end pipeline and launches Streamlit dashboard. |
| `python -m streamlit run dashboard/app.py` | Launches Streamlit dashboard directly via Python module (prevents PATH errors on Windows). |
| `python main.py --pipeline-only` | Runs full pipeline without launching UI. |
| `python main.py --dashboard-only` | Directly launches Streamlit web UI. |
| `python main.py --retrain` | Forces retraining of the XGBoost energy demand model. |
| `python main.py --test` | Executes the automated `pytest` test suite in `tests/`. |

---

## 🧪 Automated Testing

To run the automated `pytest` test suite:

```bash
python main.py --test
```
*(or `pytest tests/ -v`)*

---

## 📊 Streamlit Interactive Dashboard Features

Launch dashboard directly via:
```bash
python -m streamlit run dashboard/app.py
```
*(or run `python main.py`)*

- **Dashboard Overview**: System status banner, high-level KPI cards, workflow overview.
- **Forecasting Engine**: Plotly Actual vs Predicted lines, 24h future forecast curve, residual scatter plot, and XGBoost feature importance rankings.
- **Machine Scheduling**: Interactive Plotly Gantt chart of job execution blocks per machine, active timelines, workload allocation, and searchable schedule table.
- **Machine Analytics**: Utilization percentages (%), idle vs active power profiles, hardware specification inventory.
- **KPI Dashboard**: Metric cards for total energy cost, peak load, makespan, machine utilization, waiting time, and on-time completion rates.
- **Comparison Analysis**: Side-by-side benchmark comparison between baseline FCFS and CP-SAT optimized schedules with quantitative savings percentages.
- **Markdown Reports**: In-app viewer for technical Markdown reports (`scheduling_report.md`, `forecasting_report.md`, `dataset_summary_report.md`, `data_validation_report.md`).
- **Settings & Data Export**: Download schedules and predictions in CSV and Excel (XLSX) format.
