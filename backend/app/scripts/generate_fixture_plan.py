from datetime import UTC, datetime

from app.domain.common import DataQuality, SourceRef
from app.domain.itinerary import ExchangeRate
from app.fixtures.loader import (
    load_nanjing_places,
    load_nanjing_route_matrix,
    load_nanjing_trip_request,
    load_nanjing_weather,
)
from app.planning import DeterministicPlanner, PlanningFacts

PLANNED_AT = datetime(2026, 9, 30, tzinfo=UTC)


def build_fixture_facts() -> PlanningFacts:
    """构造完全固定、可重复运行的南京规划输入。"""
    rate_source = SourceRef(
        provider="mock",
        source_id="cny-cny-2026-09-30",
        fetched_at=PLANNED_AT,
        data_quality=DataQuality.MOCK,
    )
    cny_to_cny = ExchangeRate(
        from_currency="CNY",
        to_currency="CNY",
        rate=1.0,
        fetched_at=PLANNED_AT,
        source=rate_source,
    )
    return PlanningFacts(
        request=load_nanjing_trip_request(),
        places=tuple(load_nanjing_places()),
        weather=tuple(load_nanjing_weather()),
        route_matrix=load_nanjing_route_matrix(),
        exchange_rates={"CNY/CNY": cny_to_cny},
        planned_at=PLANNED_AT,
    )


def main() -> None:
    """生成并打印南京示例行程和约束报告。"""
    outcome = DeterministicPlanner().plan(build_fixture_facts())
    print(
        outcome.itinerary.model_dump_json(
            indent=2,
        )
    )
    print(
        outcome.report.model_dump_json(
            indent=2,
        )
    )
    print(f"planning_status={outcome.status.value}")
    print(f"attempts={outcome.attempts}")


if __name__ == "__main__":
    main()
