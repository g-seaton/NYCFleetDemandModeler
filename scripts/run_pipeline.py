from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.config import load_config
from fleetopt.data.tlc import read_trip_files
from fleetopt.features import aggregate_zone_demand, build_features
from fleetopt.forecasting import train_time_split


def main():
    parser = argparse.ArgumentParser(description="Train the demand model on TLC-style trip files.")
    parser.add_argument("--input", nargs="+", required=True)
    args = parser.parse_args()
    cfg = load_config(ROOT / "config/default.yaml")
    trips = read_trip_files(args.input)
    demand = aggregate_zone_demand(trips, cfg["project"]["interval_minutes"])
    features = build_features(demand, cfg["project"]["interval_minutes"])
    result = train_time_split(features, cfg["project"]["interval_minutes"], cfg["forecast"]["test_fraction"], cfg["forecast"])
    print(json.dumps(result.metrics, indent=2))


if __name__ == "__main__":
    main()
