from __future__ import annotations

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fleetopt.optimization import optimize_repositioning

app = FastAPI(
    title="NYC Fleet Optimizer API",
    version="0.1.0",
    description="Forecast-to-decision API for urban vehicle repositioning.",
)


class OptimizeRequest(BaseModel):
    vehicles: dict[int, int]
    forecast_demand: dict[int, float]
    cost_matrix: list[list[float]]
    solver: str = Field(default="auto", pattern="^(auto|gurobi|scipy)$")
    unmet_penalty: float = 20.0
    reposition_cost_per_minute: float = 0.35
    max_reposition_minutes: float | None = 35.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize")
def optimize(payload: OptimizeRequest):
    try:
        result = optimize_repositioning(
            payload.vehicles,
            payload.forecast_demand,
            np.asarray(payload.cost_matrix, dtype=float),
            unmet_penalty=payload.unmet_penalty,
            reposition_cost_per_minute=payload.reposition_cost_per_minute,
            max_reposition_minutes=payload.max_reposition_minutes,
            solver=payload.solver,
        )
        return {
            "status": result.status,
            "objective": result.objective,
            "moves": result.moves,
            "unmet_demand": result.unmet_demand,
            "post_reposition_vehicles": result.post_reposition_vehicles,
            "solver": result.solver,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
