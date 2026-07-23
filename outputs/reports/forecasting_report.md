# AI-Based Smart Machine Scheduling: Phase 2 Forecasting Report

## 1. Executive Summary

Phase 2 delivers an **XGBoost Regressor** time-series forecasting model designed to predict 
15-minute resolution industrial energy consumption (`Usage_kWh`). The model predictions provide 
the baseline load profile required by **Phase 3 Machine Scheduling Optimizer** to avoid high-cost peak tariff windows.

- **Primary Model Architecture**: XGBoost Regressor (`xgboost.XGBRegressor`)
- **Target Variable**: `Usage_kWh`
- **Target Resolution**: 15-Minute Intervals

---

## 2. Dataset & Time-Series Chronological Split

| Dataset Portion | Sample Count | Percentage | Date Range |
|---|---|---|---|
| **Training Set** | 28,032 | 80% | 2018-01-01 00:00:00 to 2018-10-19 23:45:00 |
| **Test Evaluation Set** | 7,008 | 20% | 2018-10-20 00:00:00 to 2018-12-31 23:45:00 |
| **Total** | 35,040 | 100% | Full Year 2018 |

> [!NOTE]
> A strictly chronological (time-series aware) split was enforced to eliminate temporal data leakage.

---

## 3. Evaluation Performance Metrics

| Metric | Definition | Value | Unit / Scale | Benchmark Performance |
|---|---|---|---|---|
| **MAE** | Mean Absolute Error | `0.5078` | kWh | Excellent (< 3.0 kWh) |
| **RMSE** | Root Mean Squared Error | `0.9976` | kWh | Low variance |
| **R² Score** | Coefficient of Determination | `0.999` | Scale 0 to 1 | High Predictive Accuracy |
| **MAPE** | Mean Absolute Percentage Error | `2.4718%` | Percentage | Strong Fit |

---

## 4. Top Feature Importance Rankings (XGBoost Gain)

The top features driving energy consumption predictions in order of gain weight:

| Rank | Feature Name | Importance Score | Feature Type / Category |
|---|---|---|---|
| 1 | `CO2(tCO2)` | 0.80983 | Electrical Power Metric |
| 2 | `Lagging_Current_Reactive.Power_kVarh` | 0.11234 | Lagged Usage Target |
| 3 | `Usage_kWh_lag_1` | 0.03500 | Lagged Usage Target |
| 4 | `Leading_Current_Power_Factor` | 0.01225 | Electrical Power Metric |
| 5 | `Usage_kWh_diff_1` | 0.00874 | Electrical Power Metric |
| 6 | `Lagging_Current_Power_Factor` | 0.00325 | Lagged Usage Target |
| 7 | `Usage_kWh_ewma_4` | 0.00292 | Rolling Statistic |
| 8 | `Leading_Current_Reactive_Power_kVarh` | 0.00255 | Electrical Power Metric |
| 9 | `day_of_year` | 0.00250 | Temporal / Calendar |
| 10 | `Usage_kWh_rolling_max_4` | 0.00173 | Rolling Statistic |
| 11 | `Usage_kWh_rolling_min_4` | 0.00111 | Rolling Statistic |
| 12 | `NSM` | 0.00079 | Temporal / Calendar |
| 13 | `WeekStatus` | 0.00066 | Temporal / Calendar |
| 14 | `hour_cos` | 0.00065 | Temporal / Calendar |
| 15 | `hour_sin` | 0.00064 | Temporal / Calendar |

---

## 5. Model Hyperparameters Configuration

```python
XGB_HYPERPARAMETERS = {'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.03, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3, 'random_state': 42, 'n_jobs': -1, 'objective': 'reg:squarederror'}
```

---

## 6. Downstream Integration Status (Phase 3 Readiness)

- **Model Artifact**: Serialized to `models/energy_xgb_model.joblib`
- **Preprocessor Artifact**: Serialized to `models/preprocessor.joblib`
- **Prediction Exports**: Saved to `outputs/forecasting/predictions.csv` and `outputs/forecasting/future_forecast.csv`
- **Visualizations**: 5 high-resolution PNG charts generated in `outputs/forecasting/`

**Status**: Phase 2 model training and forecast evaluation complete. Ready to feed forecasted energy curves into **Phase 3 Machine Scheduling Optimizer**.