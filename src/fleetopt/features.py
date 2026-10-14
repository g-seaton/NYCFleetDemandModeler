from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_zone_demand(trips: pd.DataFrame, interval_minutes: int = 30) -> pd.DataFrame:
    df = trips.copy()
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
    freq = f"{interval_minutes}min"
    df["window_start"] = df["pickup_datetime"].dt.floor(freq)
    out = (
        df.groupby(["window_start", "PULocationID"], as_index=False)
        .size()
        .rename(columns={"PULocationID": "zone_id", "size": "demand"})
    )

    # Dense grid so lags are meaningful even when a zone has zero demand.
    times = pd.date_range(out.window_start.min(), out.window_start.max(), freq=freq)
    zones = np.sort(out.zone_id.unique())
    grid = pd.MultiIndex.from_product([times, zones], names=["window_start", "zone_id"]).to_frame(index=False)
    return grid.merge(out, how="left", on=["window_start", "zone_id"]).fillna({"demand": 0})


def aggregate_od_flows(trips: pd.DataFrame, interval_minutes: int = 30) -> pd.DataFrame:
    df = trips.copy()
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
    df["window_start"] = df["pickup_datetime"].dt.floor(f"{interval_minutes}min")
    return (
        df.groupby(["window_start", "PULocationID", "DOLocationID"], as_index=False)
        .size()
        .rename(columns={"size": "trips"})
    )


def build_features(demand: pd.DataFrame, interval_minutes: int = 30) -> pd.DataFrame:
    df = demand.sort_values(["zone_id", "window_start"]).copy()
    slots_per_day = 1440 // interval_minutes
    ts = pd.to_datetime(df["window_start"])
    hour = ts.dt.hour + ts.dt.minute / 60.0
    dow = ts.dt.dayofweek

    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    df["is_weekend"] = (dow >= 5).astype(int)

    g = df.groupby("zone_id", group_keys=False)["demand"]
    for lag in [1, 2, 4, slots_per_day, 2 * slots_per_day]:
        df[f"lag_{lag}"] = g.shift(lag)
    df["rolling_4_mean"] = g.transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    df["rolling_day_mean"] = g.transform(
        lambda s: s.shift(1).rolling(slots_per_day, min_periods=4).mean()
    )
    return df.dropna().reset_index(drop=True)


def feature_columns(interval_minutes: int = 30) -> list[str]:
    slots = 1440 // interval_minutes
    return [
        "zone_id", "hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_weekend",
        "lag_1", "lag_2", "lag_4", f"lag_{slots}", f"lag_{2 * slots}",
        "rolling_4_mean", "rolling_day_mean",
    ]
