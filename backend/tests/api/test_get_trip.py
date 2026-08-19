from uuid import uuid4

from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def test_created_trip_can_be_read_again() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()

    response = client.get("/api/v1/trips/" + created["id"])

    assert response.status_code == 200
    assert response.json() == created


def test_unknown_trip_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/trips/" + str(uuid4()))

    assert response.status_code == 404


def test_list_trips_returns_trips() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()

    response = client.get("/api/v1/trips")
    assert response.status_code == 200
    trips = response.json()
    assert isinstance(trips, list)
    assert any(t["id"] == created["id"] for t in trips)
