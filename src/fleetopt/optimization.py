from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass
class OptimizationResult:
    status: str
    objective: float
    moves: list[dict[str, int]]
    unmet_demand: dict[int, float]
    post_reposition_vehicles: dict[int, int]
    solver: str


def _normalize_inputs(
    vehicles: Mapping[int, int], forecast_demand: Mapping[int, float], cost_matrix: np.ndarray
):
    zones = sorted(set(map(int, vehicles)) | set(map(int, forecast_demand)))
    if cost_matrix.shape != (len(zones), len(zones)):
        raise ValueError("cost_matrix shape must match number of zones")
    v = np.array([max(0, int(vehicles.get(z, 0))) for z in zones], dtype=float)
    d = np.array([max(0.0, float(forecast_demand.get(z, 0.0))) for z in zones], dtype=float)
    return zones, v, d


def optimize_repositioning(
    vehicles: Mapping[int, int],
    forecast_demand: Mapping[int, float],
    cost_matrix: np.ndarray,
    unmet_penalty: float = 20.0,
    reposition_cost_per_minute: float = 0.35,
    max_reposition_minutes: float | None = 35.0,
    solver: str = "auto",
) -> OptimizationResult:
    zones, v, d = _normalize_inputs(vehicles, forecast_demand, np.asarray(cost_matrix, dtype=float))
    if solver in {"auto", "gurobi"}:
        try:
            return _solve_gurobi(
                zones, v, d, np.asarray(cost_matrix, dtype=float), unmet_penalty,
                reposition_cost_per_minute, max_reposition_minutes
            )
        except Exception:
            if solver == "gurobi":
                raise
    return _solve_scipy(
        zones, v, d, np.asarray(cost_matrix, dtype=float), unmet_penalty,
        reposition_cost_per_minute, max_reposition_minutes
    )


def _allowed_arcs(costs: np.ndarray, max_minutes: float | None):
    n = costs.shape[0]
    return [(i, j) for i in range(n) for j in range(n) if i != j and (max_minutes is None or costs[i, j] <= max_minutes)]


def _solve_gurobi(zones, v, d, costs, unmet_penalty, move_cost, max_minutes):
    import gurobipy as gp
    from gurobipy import GRB

    arcs = _allowed_arcs(costs, max_minutes)
    model = gp.Model("fleet_reposition")
    model.Params.OutputFlag = 0
    x = model.addVars(arcs, vtype=GRB.INTEGER, lb=0, name="move")
    u = model.addVars(range(len(zones)), vtype=GRB.CONTINUOUS, lb=0, name="unmet")

    model.setObjective(
        gp.quicksum(move_cost * costs[i, j] * x[i, j] for i, j in arcs)
        + unmet_penalty * gp.quicksum(u[j] for j in range(len(zones))),
        GRB.MINIMIZE,
    )
    for i in range(len(zones)):
        model.addConstr(gp.quicksum(x[i, j] for ii, j in arcs if ii == i) <= v[i], name=f"supply_{i}")
    for j in range(len(zones)):
        outbound = gp.quicksum(x[j, k] for jj, k in arcs if jj == j)
        inbound = gp.quicksum(x[i, j] for i, jj in arcs if jj == j)
        model.addConstr(v[j] - outbound + inbound + u[j] >= d[j], name=f"cover_{j}")

    model.optimize()
    if model.Status not in {GRB.OPTIMAL, GRB.SUBOPTIMAL}:
        raise RuntimeError(f"Gurobi status {model.Status}")

    move_rows = []
    post = v.copy()
    for i, j in arcs:
        val = int(round(x[i, j].X))
        if val > 0:
            move_rows.append({"origin": int(zones[i]), "destination": int(zones[j]), "vehicles": val})
            post[i] -= val
            post[j] += val
    return OptimizationResult(
        status="optimal" if model.Status == GRB.OPTIMAL else "suboptimal",
        objective=float(model.ObjVal),
        moves=move_rows,
        unmet_demand={int(zones[j]): float(u[j].X) for j in range(len(zones))},
        post_reposition_vehicles={int(zones[j]): int(round(post[j])) for j in range(len(zones))},
        solver="gurobi",
    )


def _solve_scipy(zones, v, d, costs, unmet_penalty, move_cost, max_minutes):
    from scipy.optimize import Bounds, LinearConstraint, milp

    arcs = _allowed_arcs(costs, max_minutes)
    n_x = len(arcs)
    n_z = len(zones)
    n_var = n_x + n_z
    c = np.zeros(n_var)
    for k, (i, j) in enumerate(arcs):
        c[k] = move_cost * costs[i, j]
    c[n_x:] = unmet_penalty

    integrality = np.zeros(n_var, dtype=int)
    integrality[:n_x] = 1
    lb = np.zeros(n_var)
    ub = np.full(n_var, np.inf)

    rows, lower, upper = [], [], []
    for i in range(n_z):
        row = np.zeros(n_var)
        for k, (ii, _j) in enumerate(arcs):
            if ii == i:
                row[k] = 1
        rows.append(row); lower.append(-np.inf); upper.append(v[i])

    # v_j - outbound + inbound + u_j >= d_j
    # => -outbound + inbound + u_j >= d_j - v_j
    for j in range(n_z):
        row = np.zeros(n_var)
        for k, (i, jj) in enumerate(arcs):
            if i == j:
                row[k] -= 1
            if jj == j:
                row[k] += 1
        row[n_x + j] = 1
        rows.append(row); lower.append(d[j] - v[j]); upper.append(np.inf)

    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(np.vstack(rows), np.array(lower), np.array(upper)),
        options={"disp": False},
    )
    if not result.success:
        raise RuntimeError(f"MILP failed: {result.message}")

    post = v.copy()
    moves = []
    for k, (i, j) in enumerate(arcs):
        val = int(round(result.x[k]))
        if val > 0:
            moves.append({"origin": int(zones[i]), "destination": int(zones[j]), "vehicles": val})
            post[i] -= val; post[j] += val
    return OptimizationResult(
        status="optimal",
        objective=float(result.fun),
        moves=moves,
        unmet_demand={int(zones[j]): float(result.x[n_x + j]) for j in range(n_z)},
        post_reposition_vehicles={int(zones[j]): int(round(post[j])) for j in range(n_z)},
        solver="scipy-highs",
    )
