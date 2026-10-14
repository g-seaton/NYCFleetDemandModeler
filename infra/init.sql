CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS decision;

CREATE TABLE IF NOT EXISTS decision.optimization_runs (
    run_id bigserial PRIMARY KEY,
    decision_time timestamptz NOT NULL DEFAULT now(),
    forecast_version text,
    solver text NOT NULL,
    objective double precision,
    vehicles_moved integer,
    predicted_unmet double precision,
    runtime_ms double precision
);
