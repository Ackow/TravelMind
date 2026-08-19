from datetime import datetime

from app.application.facts import FactsFactory
from app.domain.common import DataQuality, SourceRef
from app.domain.itinerary import ExchangeRate
from app.domain.trip import TripRequest
from app.fixtures.loader import (
    load_nanjing_places,
    load_nanjing_route_matrix,
    load_nanjing_weather,
)
from app.planning import PlanningFacts


class NanjingFactsFactory(FactsFactory):
    """杭州 -> 南京离线教学与基准评测事实适配器。"""

    def build(self, request: TripRequest, planned_at: datetime) -> PlanningFacts:
        source = SourceRef(
            provider="mock",
            source_id="cny-stage-1",
            fetched_at=planned_at,
            data_quality=DataQuality.MOCK,
        )
        rate_cny = ExchangeRate(
            from_currency="CNY",
            to_currency="CNY",
            rate=1.0,
            fetched_at=planned_at,
            source=source,
        )
        rate_jpy = ExchangeRate(
            from_currency="JPY",
            to_currency="CNY",
            rate=0.05,
            fetched_at=planned_at,
            source=source,
        )
        rate_jpy_rev = ExchangeRate(
            from_currency="CNY",
            to_currency="JPY",
            rate=20.0,
            fetched_at=planned_at,
            source=source,
        )
        return PlanningFacts(
            request=request,
            places=tuple(load_nanjing_places()),
            weather=tuple(load_nanjing_weather()),
            route_matrix=load_nanjing_route_matrix(),
            exchange_rates={
                "CNY/CNY": rate_cny,
                "JPY/CNY": rate_jpy,
                "CNY/JPY": rate_jpy_rev,
            },
            planned_at=planned_at,
        )


# 兼容性别名
DefaultFactsFactory = NanjingFactsFactory
TokyoFactsFactory = NanjingFactsFactory
