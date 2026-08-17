from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def _clock(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%H:%M")


def test_manual_edit_creates_child_version_and_preserves_v1() -> None:
    client = TestClient(create_app())
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    base = f"/api/v1/trips/{trip['id']}"
    client.post(base + "/planning-runs")
    version_1 = client.get(base + "/plans/1").json()
    day = version_1["itinerary"]["days"][0]
    activities = [item for item in day["activities"] if item["kind"] != "transfer"]
    payload = {
        "base_plan_version": 1,
        "days": [
            {
                "date": day["date"],
                "activities": [
                    {
                        "id": item["id"],
                        "title": "浅草寺" if index == 0 else item["title"],
                        "start_time": _clock(item["start_at"]),
                        "end_time": _clock(item["end_at"]),
                        "removed": False,
                    }
                    for index, item in enumerate(activities)
                ],
            }
        ],
    }

    response = client.post(base + "/manual-edits", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["plan"]["version"] == 2
    assert body["plan"]["parent_version"] == 1
    assert body["planning_run"]["result_plan_version"] == 2
    assert client.get(base + "/plans/1").json()["version"] == 1
    assert body["plan"]["itinerary"]["days"][0]["activities"][0]["title"] == "浅草寺"


def test_manual_edit_can_add_a_known_place() -> None:
    client = TestClient(create_app())
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    base = f"/api/v1/trips/{trip['id']}"
    client.post(base + "/planning-runs")
    version_1 = client.get(base + "/plans/1").json()
    day = version_1["itinerary"]["days"][0]
    activities = [item for item in day["activities"] if item["kind"] != "transfer"]
    edits = [
        {
            "id": item["id"],
            "title": item["title"],
            "start_time": _clock(item["start_at"]),
            "end_time": _clock(item["end_at"]),
            "removed": False,
            "is_new": False,
        }
        for item in activities
    ]
    edits.append(
        {
            "id": str(uuid4()),
            "title": "明治神宫",
            "start_time": "19:00",
            "end_time": "20:00",
            "removed": False,
            "is_new": True,
        }
    )

    response = client.post(
        base + "/manual-edits",
        json={
            "base_plan_version": 1,
            "days": [{"date": day["date"], "activities": edits}],
        },
    )

    assert response.status_code == 201
    titles = [
        item["title"] for item in response.json()["plan"]["itinerary"]["days"][0]["activities"]
    ]
    assert "明治神宫" in titles
