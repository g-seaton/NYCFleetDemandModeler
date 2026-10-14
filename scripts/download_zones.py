from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.data.tlc import download_zone_assets


if __name__ == "__main__":
    lookup, archive = download_zone_assets(ROOT / "data/raw")
    print(lookup)
    print(archive)
