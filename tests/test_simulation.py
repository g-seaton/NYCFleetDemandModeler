import numpy as np
import pandas as pd

from fleetopt.simulation import simulate_policy


def test_simulation_conserves_fleet():
    times = pd.date_range("2026-01-01", periods=3, freq="30min")
    pred = pd.DataFrame([
        {"window_start": t, "zone_id": z, "demand": 2, "prediction": 2.0}
        for t in times for z in [1, 2]
    ])
    od = pd.DataFrame([
        {"window_start": t, "PULocationID": 1, "DOLocationID": 2, "trips": 2}
        for t in times
    ] + [
        {"window_start": t, "PULocationID": 2, "DOLocationID": 1, "trips": 2}
        for t in times
    ])
    result = simulate_policy(pred, od, np.array([[0, 5], [5, 0]], float), fleet_size=10, policy="optimized", solver="scipy")
    assert (result.interval_metrics["fleet_conservation"] == 10).all()
