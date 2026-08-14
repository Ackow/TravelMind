import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.domain.research import Place, RouteMatrix, WeatherDay
from app.domain.trip import TripRequest

FIXTURE_ROOT = Path(__file__).resolve().parent
TOKYO_FIXTURE_ROOT = FIXTURE_ROOT / "tokyo"


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_tokyo_trip_request() -> TripRequest:
    data = read_json(TOKYO_FIXTURE_ROOT / "trip_request.json")
    return TripRequest.model_validate(data)


def load_tokyo_weather() -> list[WeatherDay]:
    data = read_json(TOKYO_FIXTURE_ROOT / "weather.json")
    return TypeAdapter(list[WeatherDay]).validate_python(data["days"])


def load_tokyo_places() -> list[Place]:
    data = read_json(TOKYO_FIXTURE_ROOT / "places.json")
    return TypeAdapter(list[Place]).validate_python(data["places"])


def load_tokyo_route_matrix() -> RouteMatrix:
    data = read_json(TOKYO_FIXTURE_ROOT / "route_matrix.json")
    return RouteMatrix.model_validate(data)
