from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def test_start_planning_creates_first_version() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()

    response = client.post("/api/v1/trips/" + created["id"] + "/planning-runs")

    assert response.status_code == 202
    run = response.json()["planning_run"]
    assert run["status"] == "completed"
    assert run["result_plan_version"] == 1

    trip = client.get("/api/v1/trips/" + created["id"]).json()
    assert trip["status"] == "needs_review"
    assert trip["current_plan_version"] == 1
    assert trip["active_planning_run_id"] is None
