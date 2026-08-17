from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def _create_first_plan(client: TestClient) -> tuple[str, str]:
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    base = f"/api/v1/trips/{trip['id']}"
    response = client.post(base + "/planning-runs")
    assert response.status_code == 202
    return trip["id"], base


def test_feedback_preserves_v1_and_creates_v2() -> None:
    client = TestClient(create_app())
    trip_id, base = _create_first_plan(client)

    response = client.post(
        base + "/feedback",
        json={
            "base_plan_version": 1,
            "message": "每天最多走 1 公里",
            "client_operations": [
                {
                    "op": "set_max_walking",
                    "meters_per_day": 1000,
                    "reason": "用户希望减少步行",
                }
            ],
            "auto_start_replanning": True,
        },
    )

    assert response.status_code == 202
    assert response.json()["planning_run"]["result_plan_version"] == 2

    version_1 = client.get(base + "/plans/1")
    version_2 = client.get(base + "/plans/2")
    assert version_1.status_code == 200
    assert version_2.status_code == 200
    assert version_1.json()["version"] == 1
    assert version_1.json()["status"] == "superseded"
    assert version_2.json()["status"] == "valid"
    assert version_2.json()["parent_version"] == 1
    assert version_2.json()["itinerary"]["trip_id"] == trip_id
    assert all(
        day["statistics"]["walking_meters"] <= 1000 for day in version_2.json()["itinerary"]["days"]
    )

    current_trip = client.get(base).json()
    assert current_trip["current_plan_version"] == 2


def test_stale_feedback_is_rejected() -> None:
    client = TestClient(create_app())
    _, base = _create_first_plan(client)

    response = client.post(
        base + "/feedback",
        json={
            "base_plan_version": 999,
            "message": "减少步行",
            "client_operations": [{"op": "set_max_walking", "meters_per_day": 1000}],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"


def test_feedback_without_operations_requires_clarification() -> None:
    client = TestClient(create_app())
    _, base = _create_first_plan(client)

    response = client.post(
        base + "/feedback",
        json={
            "base_plan_version": 1,
            "message": "帮我调整一下",
            "client_operations": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["feedback"]["requires_clarification"] is True
    assert response.json()["planning_run"] is None
    assert response.json()["events_url"] is None
