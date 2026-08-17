from datetime import datetime

from app.application.facts import FactsFactory
from app.domain.common import DataQuality, SourceRef
from app.domain.itinerary import ExchangeRate
from app.domain.trip import TripRequest
from app.fixtures.loader import (
    load_tokyo_places,
    load_tokyo_route_matrix,
    load_tokyo_weather,
)
from app.planning import PlanningFacts


class TokyoFactsFactory(FactsFactory):
    """阶段 4 使用的固定东京事实适配器。"""

    def build(self, request: TripRequest, planned_at: datetime) -> PlanningFacts:
        # 组装固定东京 Mock 数据：地点、天气、路线矩阵和汇率
        source = SourceRef(
            provider="mock",
            source_id="jpy-cny-stage-4",
            fetched_at=planned_at,
            data_quality=DataQuality.MOCK,
        )
        rate = ExchangeRate(
            from_currency="JPY",
            to_currency="CNY",
            rate=4.8,
            fetched_at=planned_at,
            source=source,
        )
        return PlanningFacts(
            request=request,
            places=tuple(load_tokyo_places()),
            weather=tuple(load_tokyo_weather()),
            route_matrix=load_tokyo_route_matrix(),
            exchange_rates={"JPY/CNY": rate},
            planned_at=planned_at,
        )
