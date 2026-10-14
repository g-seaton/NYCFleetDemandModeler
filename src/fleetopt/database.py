from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine, text


def engine_from_env():
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://fleet:fleet@localhost:5432/fleet",
    )
    return create_engine(url, future=True)


def initialize_schemas(engine) -> None:
    with engine.begin() as conn:
        for schema in ["raw", "analytics", "decision"]:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))


def load_demo_tables(engine, trips: pd.DataFrame, zones: pd.DataFrame) -> None:
    initialize_schemas(engine)
    trips.to_sql("trips", engine, schema="raw", if_exists="replace", index=False, chunksize=5000)
    zones.to_sql("zones", engine, schema="raw", if_exists="replace", index=False)
