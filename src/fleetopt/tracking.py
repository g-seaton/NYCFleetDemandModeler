from __future__ import annotations

from typing import Any


def log_experiment(metrics: dict[str, float], params: dict[str, Any], run_name: str = "demo") -> bool:
    """Log to MLflow when installed; return False when the optional dependency is absent."""
    try:
        import mlflow
    except ImportError:
        return False
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
    return True
