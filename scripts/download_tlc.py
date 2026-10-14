from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.data.tlc import download_month


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True)
    parser.add_argument("--color", default="yellow", choices=["yellow", "green", "fhv", "fhvhv"])
    parser.add_argument("--output", default="data/raw")
    args = parser.parse_args()
    for month in args.months:
        path = download_month(args.year, month, ROOT / args.output, args.color)
        print(path)


if __name__ == "__main__":
    main()
