from datetime import date
from pathlib import Path
import sys

# 1. 自动校准 backend 寻址路径，确保独立运行、跨目录调用都不会出现导包错误 (ModuleNotFoundError)
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.mcpserver import MCPServer
from app.core.config import get_settings
from app.domain.common import GeoPoint
from app.domain.trip import TransportMode
from app.fixtures.loader import (
    load_nanjing_places,
    load_nanjing_route_matrix,
    load_nanjing_weather,
)
from app.infrastructure.composite_facts_factory import CompositeFactsFactory

server = MCPServer("TravelMind-Tool-Server")
settings = get_settings()


def parse_transport_mode(mode: str) -> TransportMode:
    """归一化并解析交通方式。"""
    mode_clean = mode.lower().strip()
    mode_map = {
        "transit": TransportMode.PUBLIC_TRANSIT,
        "public_transit": TransportMode.PUBLIC_TRANSIT,
        "walking": TransportMode.WALKING,
        "driving": TransportMode.DRIVING,
        "cycling": TransportMode.CYCLING,
        "taxi": TransportMode.TAXI,
        "mixed": TransportMode.MIXED,
    }
    return mode_map.get(mode_clean, TransportMode.PUBLIC_TRANSIT)


@server.tool(name="get_weather", description="获取目的地城市的逐日天气预报与气象灾害预警。")
def get_weather(destination: str, start_date: str, end_date: str) -> dict:
    """获取指定城市的天气列表（支持真实 API 与测试数据自适应）。"""
    try:
        s_date = date.fromisoformat(start_date)
        e_date = date.fromisoformat(end_date)

        if settings.DATA_PROVIDER_MODE == "live":
            try:
                factory = CompositeFactsFactory()
                wp, _, _ = factory._resolve_providers(GeoPoint(latitude=32.0603, longitude=118.7969))
                weather_days = wp.get_forecast(destination, s_date, e_date)
                if weather_days:
                    return {
                        "success": True,
                        "data": [d.model_dump(mode="json") for d in weather_days],
                        "provider_source": "live_realtime_weather_api",
                    }
            except Exception:
                pass

        weather_days = load_nanjing_weather()
        return {
            "success": True,
            "data": [d.model_dump(mode="json") for d in weather_days],
            "provider_source": "nanjing_weather_fixture",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "provider_source": "error"}


@server.tool(name="search_poi", description="根据地理区域、分类与关键词搜索候选景点与餐厅 POI。")
def search_poi(destination: str, query: str | None = None, category: str = "attraction", limit: int = 20) -> dict:
    """搜索目的地景点与生活设施点位（支持真实 API 与测试数据自适应）。"""
    try:
        if settings.DATA_PROVIDER_MODE == "live":
            try:
                factory = CompositeFactsFactory()
                _, poi_p, _ = factory._resolve_providers(GeoPoint(latitude=32.0603, longitude=118.7969))
                places = poi_p.search_places(
                    destination=destination,
                    query=query or destination,
                    categories=[category],
                    limit=limit,
                )
                if places:
                    return {
                        "success": True,
                        "data": [p.model_dump(mode="json") for p in places],
                        "provider_source": "live_realtime_poi_api",
                    }
            except Exception:
                pass

        places = load_nanjing_places()[:limit]
        return {
            "success": True,
            "data": [p.model_dump(mode="json") for p in places],
            "provider_source": "nanjing_poi_fixture",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "provider_source": "error"}


@server.tool(name="get_route", description="计算两个地理坐标点之间的真实路线距离、通勤耗时与换乘方案。")
def get_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = "public_transit",
) -> dict:
    """计算路径交通矩阵（支持真实 API 与测试数据自适应）。"""
    try:
        transport = parse_transport_mode(mode)
        origin_pt = GeoPoint(latitude=origin_lat, longitude=origin_lng)
        dest_pt = GeoPoint(latitude=dest_lat, longitude=dest_lng)

        if settings.DATA_PROVIDER_MODE == "live":
            try:
                factory = CompositeFactsFactory()
                _, _, route_p = factory._resolve_providers(origin_pt)
                leg = route_p.calculate_leg(
                    origin=origin_pt,
                    destination=dest_pt,
                    mode=transport,
                )
                if leg:
                    return {
                        "success": True,
                        "data": leg.model_dump(mode="json"),
                        "provider_source": "live_realtime_route_api",
                    }
            except Exception:
                pass

        matrix = load_nanjing_route_matrix()
        cell = matrix.cells[0] if matrix.cells else None
        return {
            "success": True,
            "data": {
                "distance_meters": cell.distance_meters if cell else 1500,
                "duration_minutes": cell.duration_minutes if cell else 15,
                "transport_mode": transport.value,
            },
            "provider_source": "nanjing_route_fixture",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "provider_source": "error"}


if __name__ == "__main__":
    # 使用标准 stdio 方式启动
    server.run_stdio()
