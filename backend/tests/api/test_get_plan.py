from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def test_current_returns_complete_first_plan() -> None:
    client = TestClient(create_app())
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    client.post(f"/api/v1/trips/{trip['id']}/planning-runs")

    response = client.get(f"/api/v1/trips/{trip['id']}/plans/current")

    assert response.status_code == 200
    plan = response.json()
    assert plan["version"] == 1
    assert plan["itinerary"]["trip_id"] == trip["id"]
    assert len(plan["itinerary"]["days"]) == 5
    assert plan["constraint_report"]["passed"] is True
