from datetime import date

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


@pytest.fixture
def test_facts_factory() -> CompositeFactsFactory:
    """测试用事实工厂实例。"""
    return CompositeFactsFactory()


def test_agent_full_lifecycle_with_human_approval(
    test_facts_factory: CompositeFactsFactory,
) -> None:
    """验证场景 1：Agent 顺利调研、生成、通过约束、挂起审阅并由人工批准闭环。"""
    saver = MemorySaver()
    graph = create_travel_agent_graph(facts_factory=test_facts_factory, checkpointer=saver)

    request = TripRequest(
        origin="杭州",
        destination="南京",
        destination_timezone="Asia/Shanghai",
        date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 3)),
        travelers=2,
        preferences=TripPreferences(
            pace=Pace.BALANCED,
            interests=[
                WeightedPreference(value="文化古迹", weight=0.8),
                WeightedPreference(value="美食", weight=0.9),
            ],
            transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
        ),
        constraints=TripConstraints(
            total_budget=Money(amount=500000, currency="CNY"),
            max_walking_meters_per_day=10000,
            daily_start_time="09:00",
            daily_end_time="20:00",
        ),
        locale="zh-CN",
        display_currency="CNY",
    )

    trip_id = "test_trip_nanjing_001"
    config = {"configurable": {"thread_id": trip_id}}

    initial_state = {
        "trip_id": trip_id,
        "request": request,
        "destination": "南京",
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
