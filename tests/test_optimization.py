import numpy as np

from fleetopt.optimization import optimize_repositioning


def test_optimizer_moves_surplus_to_shortage():
    vehicles = {1: 10, 2: 0, 3: 5}
    demand = {1: 2, 2: 8, 3: 4}
    costs = np.array([[0, 5, 9], [5, 0, 4], [9, 4, 0]], dtype=float)
    result = optimize_repositioning(vehicles, demand, costs, solver="scipy", unmet_penalty=50)
    assert result.status == "optimal"
    assert sum(result.post_reposition_vehicles.values()) == sum(vehicles.values())
    assert result.post_reposition_vehicles[2] >= 8
    assert sum(result.unmet_demand.values()) < 0.01
