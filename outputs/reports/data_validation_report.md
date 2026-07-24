# Data Validation Report

## Executive Summary

Automated quality validation executed across Energy, Job, and Machine datasets.

| Dataset | Dimensions | Duplicates | Total Missing Cells | Empty Cols | Invalid Warnings |
|---|---|---|---|---|---|
| Energy | 35040 x 11 | 0 | 0 | 0 | 0 |
| Job | 100 x 6 | 0 | 0 | 0 | 0 |
| Machine | 10 x 7 | 0 | 0 | 0 | 0 |

---

## Dataset: Energy
- **Dimensions**: 35040 rows, 11 columns
- **Duplicate Rows**: 0
- **Empty Columns**: None
- **Missing Values**:
  - No missing values detected.
- **Invalid Value Checks**:
  - All values within expected domain bounds.
- **Column Data Types**:
  - `date`: `str`
  - `Usage_kWh`: `float64`
  - `Lagging_Current_Reactive.Power_kVarh`: `float64`
  - `Leading_Current_Reactive_Power_kVarh`: `float64`
  - `CO2(tCO2)`: `float64`
  - `Lagging_Current_Power_Factor`: `float64`
  - `Leading_Current_Power_Factor`: `float64`
  - `NSM`: `int64`
  - `WeekStatus`: `str`
  - `Day_of_week`: `str`
  - `Load_Type`: `str`

### Basic Numerical Statistics
| Column | Mean | Std | Min | 25% | 50% | 75% | Max |
|---|---|---|---|---|---|---|---|
| `Usage_kWh` | 27.387 | 33.444 | 0.0 | 3.2 | 4.57 | 51.237 | 157.18 |
| `Lagging_Current_Reactive.Power_kVarh` | 13.035 | 16.306 | 0.0 | 2.3 | 5.0 | 22.64 | 96.91 |
| `Leading_Current_Reactive_Power_kVarh` | 3.871 | 7.424 | 0.0 | 0.0 | 0.0 | 2.09 | 27.76 |
| `CO2(tCO2)` | 0.012 | 0.016 | 0.0 | 0.0 | 0.0 | 0.02 | 0.07 |
| `Lagging_Current_Power_Factor` | 80.578 | 18.921 | 0.0 | 63.32 | 87.96 | 99.022 | 100.0 |
| `Leading_Current_Power_Factor` | 84.368 | 30.457 | 0.0 | 99.7 | 100.0 | 100.0 | 100.0 |
| `NSM` | 42750.0 | 24940.534 | 0.0 | 21375.0 | 42750.0 | 64125.0 | 85500.0 |

---

## Dataset: Job
- **Dimensions**: 100 rows, 6 columns
- **Duplicate Rows**: 0
- **Empty Columns**: None
- **Missing Values**:
  - No missing values detected.
- **Invalid Value Checks**:
  - All values within expected domain bounds.
- **Column Data Types**:
  - `Job_ID`: `str`
  - `Duration_min`: `int64`
  - `Deadline`: `str`
  - `Priority`: `str`
  - `Compatible_Machines`: `str`
  - `Arrival_Time`: `str`

### Basic Numerical Statistics
| Column | Mean | Std | Min | 25% | 50% | 75% | Max |
|---|---|---|---|---|---|---|---|
| `Duration_min` | 71.25 | 11.357 | 60.0 | 60.0 | 75.0 | 75.0 | 90.0 |

---

## Dataset: Machine
- **Dimensions**: 10 rows, 7 columns
- **Duplicate Rows**: 0
- **Empty Columns**: None
- **Missing Values**:
  - No missing values detected.
- **Invalid Value Checks**:
  - All values within expected domain bounds.
- **Column Data Types**:
  - `Machine_ID`: `str`
  - `Machine_Type`: `str`
  - `Idle_Power_kW`: `float64`
  - `Active_Power_kW`: `float64`
  - `Changeover_Time_min`: `int64`
  - `Available_From`: `str`
  - `Available_To`: `str`

### Basic Numerical Statistics
| Column | Mean | Std | Min | 25% | 50% | 75% | Max |
|---|---|---|---|---|---|---|---|
| `Idle_Power_kW` | 3.439 | 0.954 | 2.29 | 2.49 | 3.56 | 4.135 | 4.87 |
| `Active_Power_kW` | 17.067 | 4.338 | 10.48 | 14.39 | 17.065 | 20.843 | 22.71 |
| `Changeover_Time_min` | 19.8 | 7.525 | 10.0 | 12.5 | 20.0 | 27.0 | 29.0 |

---
