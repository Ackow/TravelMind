from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.clock import FixedClock
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.memory_repository import InMemoryTravelRepository
from app.main import create_app


def _client() -> TestClient:
    return TestClient(
        create_app(
            repository=InMemoryTravelRepository(),
            clock=FixedClock(datetime(2026, 9, 30, 8, 0, tzinfo=UTC)),
        )
    )


def test_plan_list_events_and_request_id_are_stable() -> None:
    client = _client()
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    base = f"/api/v1/trips/{trip['id']}"
    planning = client.post(base + "/planning-runs").json()

    plans = client.get(base + "/plans")
    events = client.get(planning["events_url"])
    missing = client.get(
        "/api/v1/trips/00000000-0000-0000-0000-000000000000",
        headers={"X-Request-ID": "stage-4-test"},
    )

    assert plans.status_code == 200
    assert plans.json()["items"][0]["version"] == 1
    assert "itinerary" not in plans.json()["items"][0]
    assert events.status_code == 200
    assert [item["sequence"] for item in events.json()["items"]] == [1, 2, 3, 4]
    assert events.json()["items"][0]["type"] == "run_started"
    assert events.json()["items"][-1]["type"] == "run_completed"
    assert missing.status_code == 404
    assert missing.headers["X-Request-ID"] == "stage-4-test"
    assert missing.json()["error"]["code"] == "TRIP_NOT_FOUND"
    assert missing.json()["error"]["request_id"] == "stage-4-test"


def test_each_app_gets_an_isolated_repository() -> None:
    first = _client()
    second = _client()
    trip = first.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()

    assert first.get(f"/api/v1/trips/{trip['id']}").status_code == 200
    assert second.get(f"/api/v1/trips/{trip['id']}").status_code == 404


def test_openapi_operation_ids_are_unique() -> None:
    schema = create_app().openapi()
    operation_ids = [
        operation["operationId"]
        for methods in schema["paths"].values()
        for method, operation in methods.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert len(operation_ids) == len(set(operation_ids))
