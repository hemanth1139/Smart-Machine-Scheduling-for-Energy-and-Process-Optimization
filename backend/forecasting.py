"""
Forecasting Engine with Tariff-Weighted Quantile Loss and Quantile XGBoost.

v2 Fixes:
  1. PF inverse-transform: predictions are multiplied by PF_SCALE=100 to restore
     the original percentage scale before writing to predictions.csv.
  2. Non-crossing post-processing: after generating p10/p50/p90 predictions,
     apply rearrangement sort (p10 <= p50 <= p90) at the observation level.
     Before/after crossing counts are both recorded for paper reporting.
  3. Recursive future forecast: ALL lag and rolling-window feature columns are
     updated at each step using the p50 prediction, not just lag_1.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional, Tuple
import xgboost as xgb
import pandas as pd
import numpy as np
import joblib

try:
    from backend.config import config
    from backend.utils import get_logger
    from backend.preprocessing import PF_SCALE
except ImportError:
    from config import config
    from utils import get_logger
    from preprocessing import PF_SCALE

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Native XGBoost quantile regression with tariff sample weights
# ---------------------------------------------------------------------------
# XGBoost 2.x+ supports objective='reg:quantileerror' natively, which uses
# the correct second-order gradient for quantile regression and avoids the
# flat-hessian saturation problem seen with custom objectives.
# Tariff importance is expressed as sample weights (not gradient modification).


# ---------------------------------------------------------------------------
# Non-crossing post-processing
# ---------------------------------------------------------------------------

def _apply_non_crossing(
    p10: np.ndarray, p50: np.ndarray, p90: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Enforce p10 <= p50 <= p90 via observation-level rearrangement (sorting).
    This is the standard post-hoc approach when quantile models are trained
    independently.
    """
    stacked = np.stack([p10, p50, p90], axis=1)   # shape (N, 3)
    stacked_sorted = np.sort(stacked, axis=1)
    return stacked_sorted[:, 0], stacked_sorted[:, 1], stacked_sorted[:, 2]


def _count_crossings(p10: np.ndarray, p50: np.ndarray, p90: np.ndarray) -> Dict[str, int]:
    c_10_50 = int(np.sum(p10 > p50))
    c_50_90 = int(np.sum(p50 > p90))
    c_10_90 = int(np.sum(p10 > p90))
    any_cross = int(np.sum((p10 > p50) | (p50 > p90) | (p10 > p90)))
    return {
        "p10_gt_p50": c_10_50,
        "p50_gt_p90": c_50_90,
        "p10_gt_p90": c_10_90,
        "total_crossing": any_cross,
        "crossing_pct": round(float(any_cross / max(len(p10), 1)) * 100.0, 4),
    }


def get_tariff_weights(X: pd.DataFrame) -> np.ndarray:
    """
    Computes sample weights based on the Load_Type column.
    Maximum_Load -> 3.0, Medium_Load -> 1.5, Light_Load -> 1.0.
    """
    if "Load_Type" in X.columns:
        col = X["Load_Type"]
        weights = np.where(
            (col == "Maximum_Load") | (col == 1.0), 3.0,
            np.where((col == "Medium_Load") | (col == 2.0), 1.5, 1.0),
        )
        return weights
    return np.ones(len(X))


# ---------------------------------------------------------------------------
# Multi-quantile forecaster
# ---------------------------------------------------------------------------

class MultiQuantileForecaster:
    """
    7 sub-models: p10/p50/p90 for Usage_kWh, p10/p50/p90 for CO2(tCO2),
    p50 only for Lagging_Current_Power_Factor (PF trained on decimal scale).
    """

    def __init__(self, hyperparams: Optional[Dict[str, Any]] = None):
        self.params = hyperparams if hyperparams is not None else config.XGB_HYPERPARAMETERS.copy()
        self.models: Dict[str, Dict[float, xgb.XGBRegressor]] = {}

        self.targets = ["Usage_kWh", "CO2(tCO2)", "Lagging_Current_Power_Factor"]
        self.quantiles = {
            "Usage_kWh": [0.10, 0.50, 0.90],
            "CO2(tCO2)": [0.10, 0.50, 0.90],
            "Lagging_Current_Power_Factor": [0.50],
        }

    def fit(self, X_train: pd.DataFrame, y_train: pd.DataFrame) -> "MultiQuantileForecaster":
        """
        Fits all 7 quantile regressors using XGBoost native 'reg:quantileerror'
        with tariff sample weights. The native objective uses correct second-order
        gradients, preventing the leaf-value saturation caused by flat hessians
        in the previous custom objective implementation.
        y_train['Lagging_Current_Power_Factor'] must already be in [0, 1] scale.
        """
        weights = get_tariff_weights(X_train)

        for target in self.targets:
            self.models[target] = {}
            for q in self.quantiles[target]:
                logger.info(f"Training Quantile XGBoost: target='{target}', q={q:.2f}")
                # Use native quantile objective — no flat-hessian saturation
                params = self.params.copy()
                params.pop("random_state", None)
                model = xgb.XGBRegressor(
                    objective="reg:quantileerror",
                    quantile_alpha=q,
                    seed=42,
                    **params,
                )
                model.fit(X_train, y_train[target], sample_weight=weights)
                self.models[target][q] = model

        logger.info("Multi-Quantile training completed.")
        return self

    def predict(self, X: pd.DataFrame) -> Dict[str, Dict[float, np.ndarray]]:
        """Generates raw predictions for all targets and quantiles (no clip, no transform)."""
        preds = {}
        for target in self.targets:
            preds[target] = {}
            for q in self.quantiles[target]:
                p = self.models[target][q].predict(X)
                # Clip at zero only — inverse-transform done in predictor
                p = np.clip(p, a_min=0.0, a_max=None)
                preds[target][q] = p
        return preds

    def save(self, filepath: Path) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"models": self.models, "params": self.params}, filepath)
        logger.info(f"Model artifacts saved to: {filepath}")

    @classmethod
    def load(cls, filepath: Path) -> "MultiQuantileForecaster":
        if not filepath.exists():
            raise FileNotFoundError(f"Model artifact not found at: {filepath}")
        data = joblib.load(filepath)
        forecaster = cls(hyperparams=data.get("params"))
        forecaster.models = data.get("models")
        return forecaster


# ---------------------------------------------------------------------------
# Predictor — test-set evaluation + future recursive forecast
# ---------------------------------------------------------------------------

class ForecastingPredictor:
    def __init__(self, forecaster: MultiQuantileForecaster):
        self.forecaster = forecaster

    # ------------------------------------------------------------------
    # Test-set evaluation
    # ------------------------------------------------------------------
    def predict_test_set(
        self,
        X_test: pd.DataFrame,
        y_test: pd.DataFrame,
        dates_test: pd.Series,
    ) -> pd.DataFrame:
        """
        Generates out-of-sample predictions on the held-out test set.

        Post-processing:
          - p10/p50/p90 for kWh and CO2 are sorted to enforce non-crossing.
          - PF predictions are inverse-transformed (* PF_SCALE) back to percent.
          - Crossing statistics before and after correction are both recorded.
        """
        preds = self.forecaster.predict(X_test)

        # Raw quantile arrays (kWh)
        raw_p10_kwh = preds["Usage_kWh"][0.10]
        raw_p50_kwh = preds["Usage_kWh"][0.50]
        raw_p90_kwh = preds["Usage_kWh"][0.90]

        # Crossing BEFORE correction
        cross_before_kwh = _count_crossings(raw_p10_kwh, raw_p50_kwh, raw_p90_kwh)

        # Non-crossing correction (rearrangement sort)
        p10_kwh, p50_kwh, p90_kwh = _apply_non_crossing(raw_p10_kwh, raw_p50_kwh, raw_p90_kwh)

        # Crossing AFTER correction — should be zero
        cross_after_kwh = _count_crossings(p10_kwh, p50_kwh, p90_kwh)

        # CO2 quantiles
        raw_p10_co2 = preds["CO2(tCO2)"][0.10]
        raw_p50_co2 = preds["CO2(tCO2)"][0.50]
        raw_p90_co2 = preds["CO2(tCO2)"][0.90]
        p10_co2, p50_co2, p90_co2 = _apply_non_crossing(raw_p10_co2, raw_p50_co2, raw_p90_co2)

        # PF (p50 only) — inverse-transform from decimal to percent
        pf_decimal = preds["Lagging_Current_Power_Factor"][0.50]
        pf_percent = pf_decimal * PF_SCALE

        # Actual PF in y_test is ALREADY in decimal (scaled by DataPreparer)
        # We store actual_PF in percent for interpretability in the CSV
        actual_pf_percent = y_test["Lagging_Current_Power_Factor"].values * PF_SCALE

        logger.info(
            f"Quantile crossing BEFORE correction: "
            f"{cross_before_kwh['total_crossing']}/{len(raw_p10_kwh)} "
            f"({cross_before_kwh['crossing_pct']}%)"
        )
        logger.info(
            f"Quantile crossing AFTER correction: "
            f"{cross_after_kwh['total_crossing']}/{len(p10_kwh)} "
            f"({cross_after_kwh['crossing_pct']}%)"
        )

        df = pd.DataFrame(
            {
                "timestamp": dates_test.values,
                # kWh
                "actual_kWh": y_test["Usage_kWh"].values,
                "predicted_kWh_p50": np.round(p50_kwh, 4),
                "predicted_kWh_p10": np.round(p10_kwh, 4),
                "predicted_kWh_p90": np.round(p90_kwh, 4),
                # Raw (before non-crossing) kept for auditing
                "raw_kWh_p10_before_nc": np.round(raw_p10_kwh, 4),
                "raw_kWh_p50_before_nc": np.round(raw_p50_kwh, 4),
                "raw_kWh_p90_before_nc": np.round(raw_p90_kwh, 4),
                # CO2
                "actual_CO2": y_test["CO2(tCO2)"].values,
                "predicted_CO2_p50": np.round(p50_co2, 6),
                "predicted_CO2_p10": np.round(p10_co2, 6),
                "predicted_CO2_p90": np.round(p90_co2, 6),
                # Power factor (both decimal and percent stored)
                "actual_PF_pct": np.round(actual_pf_percent, 4),
                "actual_PF_decimal": np.round(y_test["Lagging_Current_Power_Factor"].values, 6),
                "predicted_PF_pct": np.round(pf_percent, 4),
                "predicted_PF_decimal": np.round(pf_decimal, 6),
            }
        )
        df.to_csv(config.OUTPUT_DIR / "predictions.csv", index=False)
        logger.info(
            f"Saved predictions.csv: {len(df)} rows. "
            f"kWh pred range: [{p10_kwh.min():.3f}, {p90_kwh.max():.3f}]"
        )

        # Log crossing summary to a separate small CSV for paper reporting
        crossing_summary = pd.DataFrame(
            [
                {
                    "Target": "Usage_kWh",
                    "Stage": "Before non-crossing correction",
                    "Total_Rows": len(raw_p10_kwh),
                    **{f"kWh_{k}": v for k, v in cross_before_kwh.items()},
                },
                {
                    "Target": "Usage_kWh",
                    "Stage": "After non-crossing correction",
                    "Total_Rows": len(p10_kwh),
                    **{f"kWh_{k}": v for k, v in cross_after_kwh.items()},
                },
            ]
        )
        crossing_summary.to_csv(config.OUTPUT_DIR / "quantile_crossing_summary.csv", index=False)
        return df

    # ------------------------------------------------------------------
    # Future 48-hour recursive forecast (for scheduler)
    # ------------------------------------------------------------------
    def forecast_future_horizon(
        self,
        last_known_row: pd.DataFrame,
        last_timestamp: pd.Timestamp,
        steps: int = 96,
    ) -> pd.DataFrame:
        """
        Recursive multi-step forecast.

        Fix: At every step the following feature columns are updated using the
        p50 prediction, not just lag_1:
          - lag_1, lag_2, lag_4  (lag_96 is updated when step >= 96)
          - rolling_mean_4, rolling_std_4, rolling_min_4, rolling_max_4
          - rolling_mean_96, rolling_std_96, rolling_min_96, rolling_max_96
          - ewma_4
          - diff_1
        A sliding window buffer of recent p50 values is maintained to compute
        rolling statistics without touching any actual future values.
        """
        future_dates = [last_timestamp + pd.Timedelta(minutes=15 * (i + 1)) for i in range(steps)]
        curr_row = last_known_row.copy().iloc[[0]]

        future_kWh_p10: list = []
        future_kWh_p50: list = []
        future_kWh_p90: list = []
        future_CO2_p50: list = []
        future_CO2_p10: list = []
        future_CO2_p90: list = []
        future_PF_p50_decimal: list = []

        # Rolling buffer seeded from the last known lag/rolling features
        # We track the last 96 predictions to update lag_96 correctly.
        buffer: list = []  # grows up to 96
        if "Usage_kWh_lag_1" in curr_row.columns:
            seed_val = float(curr_row["Usage_kWh_lag_1"].iloc[0])
            buffer = [seed_val] * 96  # pre-fill so rolling stats are stable from step 0

        target_col = "Usage_kWh"

        for step_i, f_date in enumerate(future_dates):
            # --- Update temporal features ---
            for col, val in [
                ("hour", f_date.hour),
                ("day", f_date.day),
                ("month", f_date.month),
                ("day_of_week", f_date.dayofweek),
                ("is_weekend", 1 if f_date.dayofweek in [5, 6] else 0),
                ("hour_sin", np.sin(2 * np.pi * f_date.hour / 24.0)),
                ("hour_cos", np.cos(2 * np.pi * f_date.hour / 24.0)),
                ("month_sin", np.sin(2 * np.pi * (f_date.month - 1) / 12.0)),
                ("month_cos", np.cos(2 * np.pi * (f_date.month - 1) / 12.0)),
            ]:
                if col in curr_row.columns:
                    curr_row[col] = val

            # --- Predict ---
            preds = self.forecaster.predict(curr_row)
            p10 = float(preds[target_col][0.10][0])
            p50 = float(preds[target_col][0.50][0])
            p90 = float(preds[target_col][0.90][0])
            # Enforce non-crossing on single step
            p10, p50, p90 = float(min(p10, p50)), p50, float(max(p50, p90))

            co2_p10 = float(preds["CO2(tCO2)"][0.10][0])
            co2_p50 = float(preds["CO2(tCO2)"][0.50][0])
            co2_p90 = float(preds["CO2(tCO2)"][0.90][0])
            co2_p10, co2_p50, co2_p90 = (
                float(min(co2_p10, co2_p50)), co2_p50, float(max(co2_p50, co2_p90))
            )

            pf_decimal = float(preds["Lagging_Current_Power_Factor"][0.50][0])

            future_kWh_p10.append(p10)
            future_kWh_p50.append(p50)
            future_kWh_p90.append(p90)
            future_CO2_p50.append(co2_p50)
            future_CO2_p10.append(co2_p10)
            future_CO2_p90.append(co2_p90)
            future_PF_p50_decimal.append(pf_decimal)

            # --- Update all lag/rolling features using p50 ---
            buffer.append(p50)
            if len(buffer) > 96:
                buffer.pop(0)

            prev_p50 = buffer[-2] if len(buffer) >= 2 else p50

            for col in [
                f"{target_col}_lag_1",
                f"{target_col}_lag_2",
                f"{target_col}_lag_4",
            ]:
                if col in curr_row.columns:
                    lag_n = int(col.split("_lag_")[1])
                    idx = -(lag_n + 1)
                    curr_row[col] = buffer[idx] if len(buffer) > lag_n else p50

            if f"{target_col}_lag_96" in curr_row.columns:
                curr_row[f"{target_col}_lag_96"] = buffer[0]  # oldest value in window

            if f"{target_col}_diff_1" in curr_row.columns:
                curr_row[f"{target_col}_diff_1"] = p50 - prev_p50

            # Rolling window stats from buffer
            for w in [4, 96]:
                window_vals = buffer[-w:] if len(buffer) >= w else buffer
                arr = np.array(window_vals, dtype=float)
                for suffix, val in [
                    (f"rolling_mean_{w}", float(np.mean(arr))),
                    (f"rolling_std_{w}", float(np.std(arr, ddof=0))),
                    (f"rolling_min_{w}", float(np.min(arr))),
                    (f"rolling_max_{w}", float(np.max(arr))),
                ]:
                    col = f"{target_col}_{suffix}"
                    if col in curr_row.columns:
                        curr_row[col] = val

            if f"{target_col}_ewma_4" in curr_row.columns:
                old_ewma = float(curr_row[f"{target_col}_ewma_4"].iloc[0])
                alpha_ewm = 2.0 / (4 + 1)
                curr_row[f"{target_col}_ewma_4"] = old_ewma + alpha_ewm * (p50 - old_ewma)

        # Determine load type from time of day
        load_types = []
        for d in future_dates:
            if 8 <= d.hour < 18:
                load_types.append("Maximum_Load")
            elif (18 <= d.hour < 22) or (6 <= d.hour < 8):
                load_types.append("Medium_Load")
            else:
                load_types.append("Light_Load")

        # Inverse-transform PF from decimal to percent for human-readable output
        future_PF_p50_pct = [v * PF_SCALE for v in future_PF_p50_decimal]

        future_df = pd.DataFrame(
            {
                "timestamp": future_dates,
                "predicted_kWh_p10": np.round(future_kWh_p10, 3),
                "predicted_kWh_p50": np.round(future_kWh_p50, 3),
                "predicted_kWh_p90": np.round(future_kWh_p90, 3),
                "predicted_CO2_p50": np.round(future_CO2_p50, 6),
                "predicted_CO2_p10": np.round(future_CO2_p10, 6),
                "predicted_CO2_p90": np.round(future_CO2_p90, 6),
                "predicted_PF_p50": np.round(future_PF_p50_pct, 3),      # percent scale for KPI use
                "predicted_PF_p50_decimal": np.round(future_PF_p50_decimal, 6),
                "hour": [d.hour for d in future_dates],
                "day_of_week": [d.strftime("%A") for d in future_dates],
                "is_weekend": [1 if d.dayofweek in [5, 6] else 0 for d in future_dates],
                "Load_Type": load_types,
            }
        )

        future_df["predicted_kWh"] = future_df["predicted_kWh_p50"]
        future_df.to_csv(config.OUTPUT_DIR / "future_forecast.csv", index=False)
        logger.info(
            f"Saved future_forecast.csv: {len(future_df)} rows. "
            f"kWh range: [{min(future_kWh_p10):.3f}, {max(future_kWh_p90):.3f}]"
        )
        return future_df
