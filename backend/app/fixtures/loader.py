import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.domain.research import Place, RouteMatrix, WeatherDay
from app.domain.trip import TripRequest

FIXTURE_ROOT = Path(__file__).resolve().parent
NANJING_FIXTURE_ROOT = FIXTURE_ROOT / "nanjing"


def read_json(path: Path) -> Any:
    """读取 JSON 文件并返回解析后的数据。"""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


# ---------------- 杭州 -> 南京 基准测试数据加载器 (阶段 1 标准) ----------------


def load_nanjing_trip_request() -> TripRequest:
    """加载杭州 -> 南京旅行请求示例数据。"""
    data = read_json(NANJING_FIXTURE_ROOT / "trip_request.json")
    return TripRequest.model_validate(data)


def load_nanjing_weather() -> list[WeatherDay]:
    """加载南京天气预报示例数据。"""
    data = read_json(NANJING_FIXTURE_ROOT / "weather.json")
    return TypeAdapter(list[WeatherDay]).validate_python(data["days"])


def load_nanjing_places() -> list[Place]:
    """加载南京地点示例数据。"""
    data = read_json(NANJING_FIXTURE_ROOT / "places.json")
    return TypeAdapter(list[Place]).validate_python(data["places"])


def load_nanjing_route_matrix() -> RouteMatrix:
    """加载南京路线矩阵示例数据。"""
    data = read_json(NANJING_FIXTURE_ROOT / "route_matrix.json")
    return RouteMatrix.model_validate(data)


# ---------------- 兼容性别名 ----------------

load_tokyo_trip_request = load_nanjing_trip_request
load_tokyo_weather = load_nanjing_weather
load_tokyo_places = load_nanjing_places
load_tokyo_route_matrix = load_nanjing_route_matrix
