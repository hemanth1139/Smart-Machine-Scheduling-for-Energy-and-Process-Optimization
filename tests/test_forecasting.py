"""
Automated Test for Energy Forecasting Module.
"""

import pandas as pd
import numpy as np

from forecasting.xgb_model import XGBoostForecaster
from forecasting.evaluator import ForecastingEvaluator


def test_xgboost_fit_predict():
    """Tests fitting and predicting with XGBoostForecaster."""
    np.random.seed(42)
    X = pd.DataFrame({
        "feat1": np.random.rand(50),
        "feat2": np.random.rand(50),
    })
    y = pd.Series(np.random.rand(50) * 10)

    model = XGBoostForecaster(hyperparams={"n_estimators": 10, "max_depth": 3, "random_state": 42})
    model.fit(X, y)

    preds = model.predict(X)
    assert len(preds) == 50
    assert np.all(preds >= 0.0)  # Non-negative clipping check

    fi = model.get_feature_importance(["feat1", "feat2"])
    assert len(fi) == 2


def test_evaluator_metrics():
    """Tests MAE, RMSE, R2, MAPE evaluation calculations."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([11.0, 19.0, 31.0, 39.0])

    evaluator = ForecastingEvaluator()
    metrics = evaluator.evaluate(y_true, y_pred)

    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "R2" in metrics
    assert "MAPE" in metrics
    assert metrics["MAE"] == 1.0
