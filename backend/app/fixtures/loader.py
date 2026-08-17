import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.domain.research import Place, RouteMatrix, WeatherDay
from app.domain.trip import TripRequest

FIXTURE_ROOT = Path(__file__).resolve().parent
TOKYO_FIXTURE_ROOT = FIXTURE_ROOT / "tokyo"


def read_json(path: Path) -> Any:
    """读取 JSON 文件并返回解析后的数据。"""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_tokyo_trip_request() -> TripRequest:
    """加载东京旅行请求示例数据。"""
    data = read_json(TOKYO_FIXTURE_ROOT / "trip_request.json")
    return TripRequest.model_validate(data)


def load_tokyo_weather() -> list[WeatherDay]:
    """加载东京天气预报示例数据。"""
    data = read_json(TOKYO_FIXTURE_ROOT / "weather.json")
    return TypeAdapter(list[WeatherDay]).validate_python(data["days"])


def load_tokyo_places() -> list[Place]:
    """加载东京地点示例数据。"""
    data = read_json(TOKYO_FIXTURE_ROOT / "places.json")
    return TypeAdapter(list[Place]).validate_python(data["places"])


def load_tokyo_route_matrix() -> RouteMatrix:
    """加载东京路线矩阵示例数据。"""
    data = read_json(TOKYO_FIXTURE_ROOT / "route_matrix.json")
    return RouteMatrix.model_validate(data)
