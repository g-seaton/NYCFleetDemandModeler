from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.database import engine_from_env, load_demo_tables


def main():
    trips = pd.read_csv(ROOT / "data/processed/demo_trips.csv", parse_dates=["pickup_datetime", "dropoff_datetime"])
    zones = pd.read_csv(ROOT / "data/processed/demo_zones.csv")
    engine = engine_from_env()
    load_demo_tables(engine, trips, zones)
    print(f"Loaded {len(trips):,} trips and {len(zones):,} zones into PostgreSQL")


if __name__ == "__main__":
    main()
