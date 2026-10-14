from __future__ import annotations

import pandas as pd


def summarize_simulation(interval_metrics: pd.DataFrame) -> dict[str, float]:
    total_demand = float(interval_metrics["demand"].sum())
    total_served = float(interval_metrics["served"].sum())
    return {
        "total_demand": total_demand,
        "total_served": total_served,
        "total_unserved": float(interval_metrics["unserved"].sum()),
        "service_rate": total_served / total_demand if total_demand else 1.0,
        "repositioned_vehicles": float(interval_metrics["repositioned_vehicles"].sum()),
        "reposition_vehicle_minutes": float(interval_metrics["reposition_vehicle_minutes"].sum()),
        "mean_interval_service_rate": float(interval_metrics["service_rate"].mean()),
    }


def compare_policies(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in results.items():
        rows.append({"policy": name, **summarize_simulation(frame)})
    return pd.DataFrame(rows).sort_values("service_rate", ascending=False)
