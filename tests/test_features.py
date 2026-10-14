import pandas as pd

from fleetopt.features import aggregate_zone_demand, build_features


def test_feature_pipeline_builds_lags():
    times = pd.date_range("2026-01-01", periods=120, freq="30min")
    trips = pd.DataFrame({
        "pickup_datetime": list(times) * 2,
        "dropoff_datetime": list(times) * 2,
        "PULocationID": [1] * len(times) + [2] * len(times),
        "DOLocationID": [2] * len(times) + [1] * len(times),
    })
    demand = aggregate_zone_demand(trips)
    features = build_features(demand)
    assert not features.empty
    assert "lag_48" in features.columns
    assert features["lag_1"].notna().all()
