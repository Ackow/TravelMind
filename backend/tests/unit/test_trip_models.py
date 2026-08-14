from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.trip import TripRequest


def valid_trip_data() -> dict:
    return {
        "origin": "南京",
        "destination": "东京",
        "destination_timezone": "Asia/Tokyo",
        "date_range": {
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
        },
        "travelers": 2,
        "preferences": {
            "interests": [
                {"value": "动漫", "weight": 1.0},
                {"value": "美食", "weight": 0.8},
            ],
            "avoid": ["购物"],
            "dietary": [],
            "transport_modes": ["public_transit", "walking"],
            "accommodation_notes": "靠近地铁",
            "pace": "balanced",
            "must_visit_place_names": [],
        },
        "constraints": {
            "total_budget": {"amount": 1000000, "currency": "CNY"},
            "budget_is_hard_limit": True,
            "daily_start_time": "09:00",
            "daily_end_time": "21:00",
            "max_walking_meters_per_day": 12000,
            "max_activities_per_day": 5,
            "minimum_transfer_buffer_minutes": 10,
            "rest_minutes_per_day": 60,
            "required_place_names": [],
            "excluded_place_names": [],
            "accessible_only": False,
        },
        "locale": "zh-CN",
        "display_currency": "CNY",
        "notes": None,
    }


def test_trip_request_accepts_valid_mvp_trip() -> None:
    trip = TripRequest.model_validate(valid_trip_data())

    assert trip.date_range.day_count == 5
    assert trip.destination_timezone == "Asia/Tokyo"


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2026-10-01", "2026-10-02"),
        ("2026-10-01", "2026-10-08"),
    ],
)
def test_trip_request_rejects_trip_outside_mvp_day_range(
    start_date: str,
    end_date: str,
) -> None:
    data = valid_trip_data()
    data["date_range"] = {
        "start_date": start_date,
        "end_date": end_date,
    }

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_trip_request_rejects_unknown_timezone() -> None:
    data = valid_trip_data()
    data["destination_timezone"] = "Tokyo/Unknown"

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_constraints_reject_required_and_excluded_same_place() -> None:
    data = deepcopy(valid_trip_data())
    data["constraints"]["required_place_names"] = ["浅草寺"]
    data["constraints"]["excluded_place_names"] = ["浅草寺"]

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_constraints_reject_end_time_not_after_start_time() -> None:
    data = valid_trip_data()
    data["constraints"]["daily_start_time"] = "21:00"
    data["constraints"]["daily_end_time"] = "09:00"

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_trip_request_rejects_budget_currency_mismatch() -> None:
    data = valid_trip_data()
    data["display_currency"] = "JPY"

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_preferences_reject_duplicate_interests_case_insensitively() -> None:
    data = valid_trip_data()
    data["preferences"]["interests"] = [
        {"value": "Anime", "weight": 1.0},
        {"value": "anime", "weight": 0.8},
    ]

    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)
