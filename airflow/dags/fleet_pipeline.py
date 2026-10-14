from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

try:
    from airflow.decorators import dag, task
except ImportError:  # lets static tooling import the file without Airflow installed
    dag = task = None

ROOT = Path("/opt/airflow/project")

if dag is not None:
    @dag(
        dag_id="fleet_daily_pipeline",
        schedule="0 5 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["fleet", "forecasting", "optimization"],
    )
    def fleet_daily_pipeline():
        @task
        def run_demo_pipeline():
            subprocess.run(["python", str(ROOT / "scripts/bootstrap_demo.py")], check=True)

        run_demo_pipeline()

    fleet_daily_pipeline()
