from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.config import load_config
from fleetopt.data.demo import write_demo_dataset
from fleetopt.evaluation import compare_policies
from fleetopt.features import aggregate_od_flows, aggregate_zone_demand, build_features
from fleetopt.forecasting import save_model, train_time_split
from fleetopt.simulation import simulate_policy


def main():
    cfg = load_config(ROOT / "config/default.yaml")
    processed = ROOT / "data/processed"
    artifacts = ROOT / "artifacts"
    assets = ROOT / "assets"
    for p in [processed, artifacts, assets]:
        p.mkdir(parents=True, exist_ok=True)

    demo = write_demo_dataset(
        processed,
        days=24,
        interval_minutes=cfg["project"]["interval_minutes"],
        seed=cfg["project"]["seed"],
    )
    demand = aggregate_zone_demand(demo.trips, cfg["project"]["interval_minutes"])
    od = aggregate_od_flows(demo.trips, cfg["project"]["interval_minutes"])
    features = build_features(demand, cfg["project"]["interval_minutes"])
    forecast = train_time_split(
        features,
        interval_minutes=cfg["project"]["interval_minutes"],
        test_fraction=cfg["forecast"]["test_fraction"],
        model_params=cfg["forecast"],
    )
    forecast.predictions.to_csv(artifacts / "predictions.csv", index=False)
    save_model(forecast.model, artifacts / "demand_model.joblib")

    sim_cfg = cfg["simulation"]
    opt_cfg = cfg["optimization"]
    policy_results = {}
    move_files = []
    for policy in ["none", "greedy", "optimized"]:
        sim = simulate_policy(
            forecast.predictions,
            od,
            demo.travel_minutes,
            policy=policy,
            fleet_size=sim_cfg["initial_fleet_size"],
            max_intervals=sim_cfg["max_intervals"],
            unmet_penalty=opt_cfg["unmet_penalty"],
            move_cost=opt_cfg["reposition_cost_per_minute"],
            max_reposition_minutes=opt_cfg["max_reposition_minutes"],
            solver=opt_cfg["solver"],
        )
        sim.interval_metrics.to_csv(artifacts / f"simulation_{policy}.csv", index=False)
        if not sim.moves.empty:
            move_files.append(sim.moves)
        policy_results[policy] = sim.interval_metrics

    comparison = compare_policies(policy_results)
    comparison.to_csv(artifacts / "policy_comparison.csv", index=False)
    metrics = {"forecast": forecast.metrics, "policies": comparison.to_dict(orient="records")}
    (artifacts / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # GitHub-ready static visuals created from the actual demo run.
    plt.figure(figsize=(8.4, 4.6))
    order = ["none", "greedy", "optimized"]
    plot_df = comparison.set_index("policy").loc[order]
    bars = plt.bar(plot_df.index, plot_df.service_rate)
    plt.ylim(max(0, plot_df.service_rate.min() - 0.05), 1.0)
    plt.ylabel("Service rate")
    plt.title("Rolling simulation: policy comparison")
    for b, val in zip(bars, plot_df.service_rate):
        plt.text(b.get_x() + b.get_width()/2, val + 0.003, f"{val:.1%}", ha="center", fontsize=10)
    plt.tight_layout()
    plt.savefig(assets / "policy_comparison.png", dpi=180)
    plt.close()

    # Repositioning visualization for one optimized interval.
    opt_moves = pd.read_csv(artifacts / "simulation_optimized.csv")
    # Read generated move rows directly by rerunning the first interval with visible moves if available.
    all_moves = pd.concat(move_files, ignore_index=True) if move_files else pd.DataFrame()
    plt.figure(figsize=(8.4, 5.5))
    plt.scatter(demo.zones.lon, demo.zones.lat, s=160, zorder=3)
    for r in demo.zones.itertuples(index=False):
        plt.text(r.lon + 0.002, r.lat + 0.002, r.zone_name, fontsize=8)
    if not all_moves.empty:
        optimized_moves = all_moves[all_moves["policy"] == "optimized"].copy()
        totals = optimized_moves.groupby("window_start")["vehicles"].sum()
        sample_time = totals.idxmax()
        sample = optimized_moves[optimized_moves.window_start == sample_time].sort_values("vehicles", ascending=False).head(12)
        zone_lookup = demo.zones.set_index("zone_id")
        for m in sample.itertuples(index=False):
            a = zone_lookup.loc[int(m.origin)]
            b = zone_lookup.loc[int(m.destination)]
            plt.annotate(
                "", xy=(b.lon, b.lat), xytext=(a.lon, a.lat),
                arrowprops=dict(arrowstyle="->", linewidth=0.8 + 0.15 * m.vehicles, alpha=0.65),
            )
    plt.title("Example optimized vehicle repositioning")
    plt.xlabel("Longitude"); plt.ylabel("Latitude")
    plt.tight_layout()
    plt.savefig(assets / "demo_repositioning.png", dpi=180)
    plt.close()

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
