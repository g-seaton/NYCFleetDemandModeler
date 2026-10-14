from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fleetopt.optimization import optimize_repositioning


@dataclass
class SimulationResult:
    interval_metrics: pd.DataFrame
    moves: pd.DataFrame
    final_fleet: dict[int, int]


def _initial_fleet(zones: list[int], first_demand: pd.Series, fleet_size: int) -> dict[int, int]:
    weights = first_demand.reindex(zones, fill_value=1).to_numpy(dtype=float) + 1.0
    raw = weights / weights.sum() * fleet_size
    fleet = np.floor(raw).astype(int)
    remainder = fleet_size - int(fleet.sum())
    if remainder:
        for idx in np.argsort(raw - fleet)[::-1][:remainder]:
            fleet[idx] += 1
    return {z: int(v) for z, v in zip(zones, fleet)}


def greedy_reposition(vehicles, demand, costs, max_minutes=35.0):
    fleet = dict(vehicles)
    moves = []
    surplus = {z: max(0, fleet[z] - int(np.ceil(demand.get(z, 0)))) for z in fleet}
    shortage = {z: max(0, int(np.ceil(demand.get(z, 0))) - fleet[z]) for z in fleet}
    zones = sorted(fleet)
    idx = {z: i for i, z in enumerate(zones)}
    for dest in sorted(shortage, key=shortage.get, reverse=True):
        need = shortage[dest]
        while need > 0:
            origins = [o for o in zones if surplus[o] > 0 and costs[idx[o], idx[dest]] <= max_minutes]
            if not origins:
                break
            origin = min(origins, key=lambda o: costs[idx[o], idx[dest]])
            qty = min(need, surplus[origin])
            fleet[origin] -= qty; fleet[dest] += qty
            surplus[origin] -= qty; need -= qty
            moves.append({"origin": origin, "destination": dest, "vehicles": qty})
    return fleet, moves


def _serve_interval(fleet: dict[int, int], od: pd.DataFrame, zones: list[int]):
    fleet = fleet.copy()
    served = 0
    total = int(od["trips"].sum()) if not od.empty else 0
    arrivals = {z: 0 for z in zones}
    departures = {z: 0 for z in zones}
    # Serve OD rows proportionally in deterministic destination order.
    for origin in zones:
        block = od[od.PULocationID == origin].sort_values("trips", ascending=False)
        available = fleet[origin]
        for row in block.itertuples(index=False):
            qty = min(available, int(row.trips))
            if qty <= 0:
                continue
            departures[origin] += qty
            arrivals[int(row.DOLocationID)] = arrivals.get(int(row.DOLocationID), 0) + qty
            available -= qty
            served += qty
    for z in zones:
        fleet[z] = fleet[z] - departures[z] + arrivals.get(z, 0)
    return fleet, served, total - served


def simulate_policy(
    predictions: pd.DataFrame,
    od_flows: pd.DataFrame,
    cost_matrix: np.ndarray,
    policy: str = "optimized",
    fleet_size: int = 450,
    unmet_penalty: float = 20.0,
    move_cost: float = 0.35,
    max_reposition_minutes: float = 35.0,
    max_intervals: int | None = None,
    solver: str = "auto",
) -> SimulationResult:
    zones = sorted(map(int, predictions.zone_id.unique()))
    times = sorted(pd.to_datetime(predictions.window_start.unique()))
    if max_intervals:
        times = times[:max_intervals]
    first = predictions[pd.to_datetime(predictions.window_start) == times[0]].set_index("zone_id")["demand"]
    fleet = _initial_fleet(zones, first, fleet_size)
    metrics, move_rows = [], []

    for ts in times:
        frame = predictions[pd.to_datetime(predictions.window_start) == ts]
        demand = {int(r.zone_id): float(r.prediction) for r in frame.itertuples(index=False)}
        before = fleet.copy()
        moves = []
        objective = 0.0
        solver_used = "none"

        if policy == "optimized":
            opt = optimize_repositioning(
                fleet, demand, cost_matrix,
                unmet_penalty=unmet_penalty,
                reposition_cost_per_minute=move_cost,
                max_reposition_minutes=max_reposition_minutes,
                solver=solver,
            )
            fleet = opt.post_reposition_vehicles
            moves = opt.moves
            objective = opt.objective
            solver_used = opt.solver
        elif policy == "greedy":
            fleet, moves = greedy_reposition(fleet, demand, cost_matrix, max_reposition_minutes)
            solver_used = "heuristic"
        elif policy != "none":
            raise ValueError("policy must be optimized, greedy, or none")

        zone_index = {z: i for i, z in enumerate(zones)}
        move_minutes = sum(
            m["vehicles"] * cost_matrix[zone_index[m["origin"]], zone_index[m["destination"]]] for m in moves
        )
        od = od_flows[pd.to_datetime(od_flows.window_start) == ts]
        fleet, served, unserved = _serve_interval(fleet, od, zones)
        total = served + unserved
        metrics.append({
            "window_start": ts,
            "policy": policy,
            "served": served,
            "unserved": unserved,
            "demand": total,
            "service_rate": served / total if total else 1.0,
            "repositioned_vehicles": sum(m["vehicles"] for m in moves),
            "reposition_vehicle_minutes": float(move_minutes),
            "objective": float(objective),
            "solver": solver_used,
            "fleet_conservation": sum(fleet.values()),
        })
        for m in moves:
            move_rows.append({"window_start": ts, "policy": policy, **m})
        assert sum(before.values()) == sum(fleet.values()), "fleet conservation violated"

    return SimulationResult(pd.DataFrame(metrics), pd.DataFrame(move_rows), fleet)
