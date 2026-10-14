from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from fleetopt.features import feature_columns


@dataclass
class ForecastResult:
    model: object
    predictions: pd.DataFrame
    metrics: dict[str, float]
    feature_names: list[str]


def _make_model(params: dict | None = None):
    params = params or {}
    try:
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=int(params.get("n_estimators", 250)),
            max_depth=int(params.get("max_depth", 5)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=4,
        )
    except Exception:
        return HistGradientBoostingRegressor(
            max_iter=int(params.get("n_estimators", 250)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            max_leaf_nodes=31,
            random_state=42,
        )


def train_time_split(
    features: pd.DataFrame,
    interval_minutes: int = 30,
    test_fraction: float = 0.2,
    model_params: dict | None = None,
) -> ForecastResult:
    cols = feature_columns(interval_minutes)
    times = np.array(sorted(pd.to_datetime(features.window_start).unique()))
    split_idx = max(1, int(len(times) * (1 - test_fraction)))
    cutoff = times[split_idx]
    train = features[pd.to_datetime(features.window_start) < cutoff].copy()
    test = features[pd.to_datetime(features.window_start) >= cutoff].copy()

    model = _make_model(model_params)
    model.fit(train[cols], train["demand"])
    pred = np.clip(model.predict(test[cols]), 0, None)

    slots = 1440 // interval_minutes
    seasonal_col = f"lag_{slots}"
    baseline = np.clip(test[seasonal_col].to_numpy(), 0, None)

    metrics = {
        "mae_model": float(mean_absolute_error(test["demand"], pred)),
        "rmse_model": float(mean_squared_error(test["demand"], pred) ** 0.5),
        "mae_seasonal_naive": float(mean_absolute_error(test["demand"], baseline)),
        "rmse_seasonal_naive": float(mean_squared_error(test["demand"], baseline) ** 0.5),
    }
    predictions = test[["window_start", "zone_id", "demand"]].copy()
    predictions["prediction"] = pred
    predictions["seasonal_naive"] = baseline
    return ForecastResult(model=model, predictions=predictions, metrics=metrics, feature_names=cols)


def save_model(model: object, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
