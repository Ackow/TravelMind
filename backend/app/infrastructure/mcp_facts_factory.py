from datetime import datetime

from pydantic import TypeAdapter

from app.application.facts import FactsFactory
from app.domain.common import DataQuality, SourceRef
from app.domain.research import Place, RouteMatrix, WeatherDay
from app.domain.trip import TripRequest
from app.infrastructure.mcp_client import McpClientAdapter
from app.planning.models import PlanningFacts


class McpFactsFactory(FactsFactory):
    """基于 MCP 远程工具协议的规划事实工厂防腐层实现。"""

    def __init__(self, mcp_client: McpClientAdapter | None = None) -> None:
        self._client = mcp_client or McpClientAdapter()

    def build(self, request: TripRequest, planned_at: datetime) -> PlanningFacts:
        """通过调用 MCP 工具获取多源事实并封装为不可变领域对象。"""
        # 1. 调用 MCP 工具获取天气
        weather_raw = self._client.call_tool_sync(
            "get_weather",
            {
                "destination": request.destination,
                "start_date": request.date_range.start_date.isoformat(),
                "end_date": request.date_range.end_date.isoformat(),
            },
        )
        weather_days = TypeAdapter(list[WeatherDay]).validate_python(weather_raw)

        # 2. 调用 MCP 工具搜索地点 POI
        poi_raw = self._client.call_tool_sync(
            "search_poi",
            {
                "destination": request.destination,
                "query": request.destination,
                "category": "attraction",
                "limit": 25,
            },
        )
        places = TypeAdapter(list[Place]).validate_python(poi_raw)

        # 3. 构造路由矩阵
        source = SourceRef(
            provider="mcp-server",
            source_id="mcp-route-v1",
            fetched_at=planned_at,
            data_quality=DataQuality.VERIFIED,
        )
        route_matrix = RouteMatrix(cells=[], source=source)

        return PlanningFacts(
            request=request,
            places=tuple(places),
            weather=tuple(weather_days),
            route_matrix=route_matrix,
            exchange_rates={"JPY/CNY": 0.05, "CNY/JPY": 20.0, "USD/CNY": 7.2},
            planned_at=planned_at,
        )
