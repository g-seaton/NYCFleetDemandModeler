from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DemoData:
    trips: pd.DataFrame
    zones: pd.DataFrame
    travel_minutes: np.ndarray


def make_zones(n_zones: int = 12) -> pd.DataFrame:
    # Pseudo-NYC centroids laid out to produce meaningful spatial structure.
    names = [
        "Midtown", "Upper East", "Upper West", "Chelsea", "SoHo", "Lower East",
        "Downtown BK", "Williamsburg", "LIC", "Astoria", "JFK Area", "Harlem",
    ][:n_zones]
    boroughs = [
        "Manhattan", "Manhattan", "Manhattan", "Manhattan", "Manhattan", "Manhattan",
        "Brooklyn", "Brooklyn", "Queens", "Queens", "Queens", "Manhattan",
    ][:n_zones]
    coords = np.array([
        [40.7549, -73.9840], [40.7736, -73.9566], [40.7870, -73.9754],
        [40.7465, -74.0014], [40.7233, -74.0030], [40.7182, -73.9881],
        [40.6928, -73.9903], [40.7180, -73.9584], [40.7447, -73.9485],
        [40.7644, -73.9235], [40.6413, -73.7781], [40.8116, -73.9465],
    ])[:n_zones]
    return pd.DataFrame({
        "zone_id": np.arange(1, n_zones + 1),
        "zone_name": names,
        "borough": boroughs,
        "lat": coords[:, 0],
        "lon": coords[:, 1],
    })


def _haversine_minutes(zones: pd.DataFrame) -> np.ndarray:
    lat = np.radians(zones["lat"].to_numpy())
    lon = np.radians(zones["lon"].to_numpy())
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    km = 6371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    # Dense city driving proxy: 22 km/h + 3 minute fixed overhead.
    mins = km / 22.0 * 60.0 + 3.0
    np.fill_diagonal(mins, 0.0)
    return mins


def generate_demo_data(
    days: int = 24,
    interval_minutes: int = 30,
    seed: int = 42,
    n_zones: int = 12,
) -> DemoData:
    rng = np.random.default_rng(seed)
    zones = make_zones(n_zones)
    travel_minutes = _haversine_minutes(zones)
    periods = pd.date_range("2026-01-05", periods=days * (1440 // interval_minutes), freq=f"{interval_minutes}min")

    base = np.array([14, 9, 8, 11, 10, 9, 7, 8, 9, 7, 5, 6], dtype=float)[:n_zones]
    rows: list[dict] = []

    # Destination attraction varies by zone and time, creating fleet drift.
    zone_ids = zones["zone_id"].to_numpy()
    for ts in periods:
        hour = ts.hour + ts.minute / 60
        dow = ts.dayofweek
        weekday = 1.0 if dow < 5 else 0.84
        morning = np.exp(-0.5 * ((hour - 8.5) / 1.8) ** 2)
        evening = np.exp(-0.5 * ((hour - 18.0) / 2.1) ** 2)
        night = np.exp(-0.5 * ((hour - 23.0) / 2.3) ** 2)

        spatial = np.ones(n_zones)
        spatial[:6] += 0.65 * evening
        if n_zones > 6:
            spatial[6:10] += 0.55 * morning
        if n_zones > 10:
            spatial[10] += 0.75 * (np.exp(-0.5 * ((hour - 6.5) / 2.0) ** 2) + evening)
        spatial[0] += 0.8 * morning + 0.7 * evening
        spatial[min(4, n_zones - 1)] += 0.55 * night

        lam = base * weekday * (0.55 + 0.85 * morning + 0.9 * evening + 0.45 * night) * spatial
        lam *= rng.lognormal(mean=0.0, sigma=0.08, size=n_zones)
        origin_counts = rng.poisson(np.maximum(lam, 0.2))

        for oi, count in enumerate(origin_counts):
            if count == 0:
                continue
            distance_decay = np.exp(-travel_minutes[oi] / 19.0)
            attraction = base.copy()
            attraction[:6] *= 1.0 + 0.9 * morning
            if n_zones > 6:
                attraction[6:10] *= 1.0 + 0.75 * evening
            probs = distance_decay * attraction
            probs[oi] *= 0.35
            probs /= probs.sum()
            dests = rng.choice(np.arange(n_zones), size=int(count), p=probs)
            for di in dests:
                duration = max(4.0, travel_minutes[oi, di] * rng.normal(1.0, 0.12))
                rows.append({
                    "pickup_datetime": ts,
                    "dropoff_datetime": ts + pd.Timedelta(minutes=float(duration)),
                    "PULocationID": int(zone_ids[oi]),
                    "DOLocationID": int(zone_ids[di]),
                    "trip_distance": max(0.4, duration * 22 / 60),
                })

    trips = pd.DataFrame(rows)
    return DemoData(trips=trips, zones=zones, travel_minutes=travel_minutes)


def write_demo_dataset(output_dir: str | Path, **kwargs) -> DemoData:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    demo = generate_demo_data(**kwargs)
    demo.trips.to_csv(output / "demo_trips.csv", index=False)
    demo.zones.to_csv(output / "demo_zones.csv", index=False)
    pd.DataFrame(demo.travel_minutes, index=demo.zones.zone_id, columns=demo.zones.zone_id).to_csv(
        output / "demo_travel_minutes.csv"
    )
    return demo
