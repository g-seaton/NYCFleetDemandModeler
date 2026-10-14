from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

TRIP_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZONE_ARCHIVE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"


def tlc_trip_url(year: int, month: int, color: str = "yellow") -> str:
    if color not in {"yellow", "green", "fhv", "fhvhv"}:
        raise ValueError("color must be one of: yellow, green, fhv, fhvhv")
    return f"{TRIP_BASE}/{color}_tripdata_{year}-{month:02d}.parquet"


def download_month(year: int, month: int, output_dir: str | Path, color: str = "yellow") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{color}_tripdata_{year}-{month:02d}.parquet"
    url = tlc_trip_url(year, month, color)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return path



def download_zone_assets(output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    lookup_path = output / "taxi_zone_lookup.csv"
    zones_path = output / "taxi_zones.zip"
    for url, path in [(ZONE_LOOKUP_URL, lookup_path), (ZONE_ARCHIVE_URL, zones_path)]:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
    return lookup_path, zones_path


def normalize_tlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    candidates = {
        "tpep_pickup_datetime": "pickup_datetime",
        "lpep_pickup_datetime": "pickup_datetime",
        "pickup_datetime": "pickup_datetime",
        "tpep_dropoff_datetime": "dropoff_datetime",
        "lpep_dropoff_datetime": "dropoff_datetime",
        "dropOff_datetime": "dropoff_datetime",
        "dropoff_datetime": "dropoff_datetime",
    }
    renamed = df.rename(columns={c: candidates[c] for c in df.columns if c in candidates})
    needed = {"pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID"}
    missing = needed - set(renamed.columns)
    if missing:
        raise ValueError(f"Missing required TLC columns: {sorted(missing)}")
    out = renamed.copy()
    out["pickup_datetime"] = pd.to_datetime(out["pickup_datetime"], errors="coerce")
    out["dropoff_datetime"] = pd.to_datetime(out["dropoff_datetime"], errors="coerce")
    out = out.dropna(subset=["pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID"])
    out = out[(out.PULocationID > 0) & (out.DOLocationID > 0)]
    return out


def read_trip_files(paths: list[str | Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        p = Path(path)
        if p.suffix.lower() == ".parquet":
            frame = pd.read_parquet(p)
        else:
            frame = pd.read_csv(p)
        frames.append(normalize_tlc_columns(frame))
    return pd.concat(frames, ignore_index=True)
