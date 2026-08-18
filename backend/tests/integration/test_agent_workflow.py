from datetime import date, datetime, UTC
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from app.agent.graph import create_travel_agent_graph
from app.agent.state import PlanStatus
from app.domain.common import DateRange, Money
from app.domain.trip import (
    Pace,
    TransportMode,
    TripConstraints,
    TripPreferences,
    TripRequest,
    WeightedPreference,
)
from app.infrastructure.composite_facts_factory import CompositeFactsFactory
from app.providers.poi.amap import AmapPoiProvider
from app.providers.route.amap import AmapRouteProvider
from app.providers.weather.amap import AmapWeatherProvider


@pytest.fixture
def test_facts_factory() -> CompositeFactsFactory:
    """测试用事实工厂实例。"""
    return CompositeFactsFactory()


def test_agent_full_lifecycle_with_human_approval(test_facts_factory: CompositeFactsFactory) -> None:
    """验证场景 1：Agent 顺利调研、生成、通过约束、挂起审阅并由人工批准闭环。"""
    saver = MemorySaver()
    graph = create_travel_agent_graph(facts_factory=test_facts_factory, checkpointer=saver)

    request = TripRequest(
        origin="Shanghai",
        destination="Tokyo",
        destination_timezone="Asia/Tokyo",
        date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 3)),
        travelers=2,
        preferences=TripPreferences(
            pace=Pace.BALANCED,
            interests=[WeightedPreference(value="culture", weight=0.8), WeightedPreference(value="food", weight=0.9)],
            transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
        ),
        constraints=TripConstraints(
            total_budget=Money(amount=1000000, currency="JPY"),
            max_walking_meters_per_day=10000,
            daily_start_time="09:00",
            daily_end_time="20:00",
        ),
        locale="zh-CN",
        display_currency="JPY",
    )

    trip_id = "test_trip_tokyo_001"
    config = {"configurable": {"thread_id": trip_id}}

    initial_state = {
        "trip_id": trip_id,
        "request": request,
        "destination": "Tokyo",
        "repair_attempts": 0,
        "max_repair_attempts": 3,
        "applied_repairs": [],
        "status": PlanStatus.INIT,
        "audit_events": [],
    }

    # 1. 首次触发执行 -> 必须停留在人在回路挂起点 (human_interrupt)
    state_after_stream = graph.invoke(initial_state, config=config)

    # 检查状态是否挂起在 AWAITING_REVIEW
    current_snapshot = graph.get_state(config)
    assert current_snapshot.next == ("human_interrupt",)
    assert state_after_stream["current_itinerary"] is not None
    assert state_after_stream["review_summary"] is not None
    print(f"\n[Agent 挂起审阅输出]:\n{state_after_stream['review_summary']}")

    # 2. 模拟用户审阅并点击【确认批准】
    final_state = graph.invoke(
        Command(resume={"action": "approve"}),
        config=config,
    )

    # 3. 验证最终状态确立为 APPROVED，行程版本完整
    assert final_state["status"] == PlanStatus.APPROVED
    assert len(final_state["current_itinerary"].days) == 3
    print("\n[PASS] Agent 全生命周期（研究 -> 规划 -> 约束 -> 挂起 -> 批准）验证圆满通过！")