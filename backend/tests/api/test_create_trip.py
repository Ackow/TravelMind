from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def test_create_trip_returns_server_fields() -> None:
    client = TestClient(create_app())
    payload = load_tokyo_trip_request().model_dump(mode="json")

    response = client.post("/api/v1/trips", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["status"] == "draft"
    assert body["revision"] == 1
    assert body["destination"] == "南京"
    assert response.headers["location"] == f"/api/v1/trips/{body['id']}"
    assert response.headers["etag"] == '"1"'


def test_create_trip_rejects_invalid_body() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/trips",
        json={"destination": "东京"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]
