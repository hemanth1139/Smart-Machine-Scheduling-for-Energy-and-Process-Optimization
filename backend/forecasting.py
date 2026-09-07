"""
Forecasting Engine with Tariff-Weighted Quantile Loss and Quantile XGBoost.
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
except ImportError:
    from config import config
    from utils import get_logger

logger = get_logger(__name__)


def get_tariff_weights(X: pd.DataFrame) -> np.ndarray:
    """
    Computes sample weights based on the Load_Type column.
    Load_Type values: Maximum_Load (1.0) -> weight 3.0, Medium_Load (2.0) -> weight 1.5, Light_Load (0.0) -> weight 1.0.
    """
    if "Load_Type" in X.columns:
        col = X["Load_Type"]
        # Map categories to weights
        weights = np.where((col == "Maximum_Load") | (col == 1.0), 3.0,
                           np.where((col == "Medium_Load") | (col == 2.0), 1.5, 1.0))
        return weights
    return np.ones(len(X))


class TariffWeightedQuantileObjective:
    """
    Custom objective callable class for tariff-weighted quantile regression.
    This class is defined at the module level so that it is picklable by joblib.
    """
    def __init__(self, alpha: float, weights: np.ndarray):
        self.alpha = alpha
        self.weights = weights

    def __call__(self, y_true: np.ndarray, dtrain: Union[xgb.DMatrix, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        # Handle cases where dtrain is a numpy array or DMatrix
        if isinstance(dtrain, xgb.DMatrix):
            y_pred = y_true # in custom objective, first argument is predictions when using standard xgb
            y_true_labels = dtrain.get_label()
        else:
            # For some xgboost versions Scikit-Learn API: custom_obj(y_true, y_pred)
            y_pred = dtrain
            y_true_labels = y_true

        errors = y_true_labels - y_pred
        
        # Gradient = -alpha if error >= 0 else 1 - alpha
        grad = np.where(errors >= 0, -self.alpha, 1.0 - self.alpha) * self.weights
        
        # Hessian is approximated as a positive constant scaled by weights
        hess = np.ones_like(y_true_labels) * self.weights
        
        return grad, hess


class MultiQuantileForecaster:
    """
    Manages 7 sub-models to forecast p10, p50, p90 for active load and carbon, and p50 for power factor.
    """

    def __init__(self, hyperparams: Optional[Dict[str, Any]] = None):
        self.params = hyperparams if hyperparams is not None else config.XGB_HYPERPARAMETERS.copy()
        self.models: Dict[str, Dict[float, xgb.XGBRegressor]] = {}
        
        self.targets = ["Usage_kWh", "CO2(tCO2)", "Lagging_Current_Power_Factor"]
        self.quantiles = {
            "Usage_kWh": [0.10, 0.50, 0.90],
            "CO2(tCO2)": [0.10, 0.50, 0.90],
            "Lagging_Current_Power_Factor": [0.50]
        }

    def fit(self, X_train: pd.DataFrame, y_train: pd.DataFrame) -> "MultiQuantileForecaster":
        """
        Fits all 7 quantile regressors with tariff-weighted custom loss.
        """
        weights = get_tariff_weights(X_train)
        
        for target in self.targets:
            self.models[target] = {}
            for q in self.quantiles[target]:
                logger.info(f"Training Quantile XGBoost for target '{target}', quantile {q:.2f}...")
                
                # Instantiate custom objective class
                obj = TariffWeightedQuantileObjective(q, weights)
                
                # Create model
                model = xgb.XGBRegressor(
                    objective=obj,
                    **self.params
                )
                
                # Train model
                model.fit(X_train, y_train[target])
                self.models[target][q] = model
                
        logger.info("Multi-Quantile training completed successfully.")
        return self

    def predict(self, X: pd.DataFrame) -> Dict[str, Dict[float, np.ndarray]]:
        """
        Generates predictions for all targets and quantiles.
        """
        preds = {}
        for target in self.targets:
            preds[target] = {}
            for q in self.quantiles[target]:
                model = self.models[target][q]
                p = model.predict(X)
                # Lower bound clip
                p = np.clip(p, a_min=0.0, a_max=None)
                preds[target][q] = p
        return preds

    def save(self, filepath: Path) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"models": self.models, "params": self.params}, filepath)
        logger.info(f"Multi-Quantile model artifacts saved to: {filepath}")

    @classmethod
    def load(cls, filepath: Path) -> "MultiQuantileForecaster":
        if not filepath.exists():
            raise FileNotFoundError(f"Model artifact not found at: {filepath}")
        data = joblib.load(filepath)
        forecaster = cls(hyperparams=data.get("params"))
        forecaster.models = data.get("models")
        return forecaster


class ForecastingPredictor:
    def __init__(self, forecaster: MultiQuantileForecaster):
        self.forecaster = forecaster

    def predict_test_set(self, X_test: pd.DataFrame, y_test: pd.DataFrame, dates_test: pd.Series) -> pd.DataFrame:
        preds = self.forecaster.predict(X_test)
        
        results = {
            "timestamp": dates_test.values,
            "actual_kWh": y_test["Usage_kWh"].values,
            "predicted_kWh_p50": preds["Usage_kWh"][0.50],
            "predicted_kWh_p10": preds["Usage_kWh"][0.10],
            "predicted_kWh_p90": preds["Usage_kWh"][0.90],
            "actual_CO2": y_test["CO2(tCO2)"].values,
            "predicted_CO2_p50": preds["CO2(tCO2)"][0.50],
            "actual_PF": y_test["Lagging_Current_Power_Factor"].values,
            "predicted_PF_p50": preds["Lagging_Current_Power_Factor"][0.50],
        }
        
        df = pd.DataFrame(results)
        df.to_csv(config.OUTPUT_DIR / "predictions.csv", index=False)
        return df

    def forecast_future_horizon(self, last_known_row: pd.DataFrame, last_timestamp: pd.Timestamp, steps: int = 96) -> pd.DataFrame:
        """
        Generates recursive multi-step forecasting for the next 24 hours.
        """
        future_dates = [last_timestamp + pd.Timedelta(minutes=15 * (i + 1)) for i in range(steps)]
        curr_row = last_known_row.copy().iloc[[0]]
        
        future_kWh_p10 = []
        future_kWh_p50 = []
        future_kWh_p90 = []
        future_CO2_p50 = []
        future_PF_p50 = []

        for f_date in future_dates:
            # Update temporal features
            if "hour" in curr_row.columns:
                curr_row["hour"] = f_date.hour
            if "day" in curr_row.columns:
                curr_row["day"] = f_date.day
            if "month" in curr_row.columns:
                curr_row["month"] = f_date.month
            if "day_of_week" in curr_row.columns:
                curr_row["day_of_week"] = f_date.dayofweek
            if "is_weekend" in curr_row.columns:
                curr_row["is_weekend"] = 1 if f_date.dayofweek in [5, 6] else 0
            if "hour_sin" in curr_row.columns:
                curr_row["hour_sin"] = np.sin(2 * np.pi * f_date.hour / 24.0)
            if "hour_cos" in curr_row.columns:
                curr_row["hour_cos"] = np.cos(2 * np.pi * f_date.hour / 24.0)

            # Predict
            preds = self.forecaster.predict(curr_row)
            
            p10 = float(preds["Usage_kWh"][0.10][0])
            p50 = float(preds["Usage_kWh"][0.50][0])
            p90 = float(preds["Usage_kWh"][0.90][0])
            co2 = float(preds["CO2(tCO2)"][0.50][0])
            pf = float(preds["Lagging_Current_Power_Factor"][0.50][0])

            future_kWh_p10.append(p10)
            future_kWh_p50.append(p50)
            future_kWh_p90.append(p90)
            future_CO2_p50.append(co2)
            future_PF_p50.append(pf)

            # Update lag_1 column for next step
            lag_1_col = "Usage_kWh_lag_1"
            if lag_1_col in curr_row.columns:
                curr_row[lag_1_col] = p50

        # Construct load type based on time
        load_types = []
        for d in future_dates:
            # 8 to 20 maximum load, rest light/medium
            if 8 <= d.hour < 18:
                load_types.append("Maximum_Load")
            elif (18 <= d.hour < 22) or (6 <= d.hour < 8):
                load_types.append("Medium_Load")
            else:
                load_types.append("Light_Load")

        future_df = pd.DataFrame({
            "timestamp": future_dates,
            "predicted_kWh_p10": np.round(future_kWh_p10, 3),
            "predicted_kWh_p50": np.round(future_kWh_p50, 3),
            "predicted_kWh_p90": np.round(future_kWh_p90, 3),
            "predicted_CO2_p50": np.round(future_CO2_p50, 3),
            "predicted_PF_p50": np.round(future_PF_p50, 3),
            "hour": [d.hour for d in future_dates],
            "day_of_week": [d.strftime("%A") for d in future_dates],
            "is_weekend": [1 if d.dayofweek in [5, 6] else 0 for d in future_dates],
            "Load_Type": load_types
        })
        
        future_df.to_csv(config.OUTPUT_DIR / "future_forecast.csv", index=False)
        return future_df
