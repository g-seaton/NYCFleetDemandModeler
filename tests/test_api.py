from fastapi.testclient import TestClient

from fleetopt.api.main import app


def test_health():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_optimize_endpoint():
    client = TestClient(app)
    response = client.post("/optimize", json={
        "vehicles": {"1": 10, "2": 0},
        "forecast_demand": {"1": 2, "2": 8},
        "cost_matrix": [[0, 5], [5, 0]],
        "solver": "scipy",
        "unmet_penalty": 50,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "optimal"
