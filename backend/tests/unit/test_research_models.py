from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.research import OpeningPeriod, Place, RouteMatrix, RouteMatrixCell, WeatherDay


def mock_source() -> dict:
    return {
        "provider": "mock",
        "source_id": "fixture",
        "source_url": None,
        "fetched_at": datetime(2026, 8, 13, 0, 0, tzinfo=UTC).isoformat(),
        "expires_at": None,
        "data_quality": "mock",
    }


def test_weather_rejects_invalid_probability() -> None:
    with pytest.raises(ValidationError):
        WeatherDay.model_validate(
            {
                "date": "2026-10-01",
                "condition": "rain",
                "temperature_min_c": 18,
                "temperature_max_c": 22,
                "rain_probability": 1.2,
                "precipitation_mm": 8,
                "sunrise_time": "05:35",
                "sunset_time": "17:25",
                "outdoor_suitability": "poor",
                "source": mock_source(),
            }
        )


def test_open_period_requires_times() -> None:
    with pytest.raises(ValidationError):
        OpeningPeriod(day_of_week=1, closed=False)


def test_place_requires_coordinates() -> None:
    with pytest.raises(ValidationError):
        Place.model_validate(
            {
                "id": "tm_place_sensoji",
                "name": "浅草寺",
                "categories": ["temple"],
                "estimated_visit_minutes": 90,
                "indoor_outdoor": "outdoor",
                "source": mock_source(),
            }
        )


def test_ok_route_cell_requires_metrics() -> None:
    with pytest.raises(ValidationError):
        RouteMatrixCell.model_validate(
            {
                "origin_place_id": "a",
                "destination_place_id": "b",
                "mode": "public_transit",
                "status": "ok",
                "duration_minutes": None,
                "distance_meters": None,
                "walking_meters": None,
                "cost": None,
            }
        )


def test_weather_rejects_inverted_temperature_range() -> None:
    with pytest.raises(ValidationError):
        WeatherDay.model_validate(
            {
                "date": "2026-10-01",
                "condition": "clear",
                "temperature_min_c": 26,
                "temperature_max_c": 20,
                "outdoor_suitability": "good",
                "source": mock_source(),
            }
        )


def test_opening_period_rejects_invalid_weekday() -> None:
    with pytest.raises(ValidationError):
        OpeningPeriod(day_of_week=8, open_time="09:00", close_time="17:00", closed=False)


def test_place_rejects_invalid_rating() -> None:
    with pytest.raises(ValidationError):
        Place.model_validate(
            {
                "id": "tm_place_invalid_rating",
                "name": "非法评分地点",
                "categories": ["attraction"],
                "location": {"latitude": 35.0, "longitude": 139.0},
                "rating": 5.1,
                "estimated_visit_minutes": 60,
                "indoor_outdoor": "outdoor",
                "source": mock_source(),
            }
        )


def test_route_matrix_rejects_duplicate_route_keys() -> None:
    cell = {
        "origin_place_id": "a",
        "destination_place_id": "b",
        "mode": "public_transit",
        "status": "ok",
        "duration_minutes": 10,
        "distance_meters": 1000,
        "walking_meters": 100,
        "cost": None,
    }

    with pytest.raises(ValidationError):
        RouteMatrix.model_validate({"cells": [cell, cell], "source": mock_source()})
