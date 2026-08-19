from uuid import uuid4

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.agent.graph import create_travel_agent_graph
from app.agent.state import PlanStatus
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.tokyo_facts_factory import TokyoFactsFactory


def test_agent_interrupt_and_resume_across_restarts(tmp_path):
    """验证：Agent 在 human_interrupt 挂起后，模拟进程重启，从持久化 Checkpoint 唤醒并完成。"""
    trip_id = f"trip_{uuid4()}"
    config = {"configurable": {"thread_id": trip_id}}
    factory = TokyoFactsFactory()
    db_file = tmp_path / "test_checkpoints.db"

    request = load_tokyo_trip_request()

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

    # 1. 第一次启动图执行（第一次编译，使用独立 SQLite 检查点文件）
    with SqliteSaver.from_conn_string(str(db_file)) as checkpointer_1:
        agent_1 = create_travel_agent_graph(factory, checkpointer=checkpointer_1)
        state_1 = agent_1.invoke(initial_state, config=config)

        # 验证此时图状态挂起在 human_interrupt，产出了初版 Itinerary
        current_snapshot = agent_1.get_state(config)
        assert current_snapshot.next == ("human_interrupt",)
        assert state_1.get("current_itinerary") is not None
        assert state_1.get("status") == PlanStatus.AWAITING_REVIEW

    # 2. 模拟进程彻底销毁并重启（重新打开连接构建图实例，加载同一持久化 Checkpoint）
    with SqliteSaver.from_conn_string(str(db_file)) as checkpointer_2:
        agent_2 = create_travel_agent_graph(factory, checkpointer=checkpointer_2)

        # 3. 发送 resume 指令唤醒执行
        resume_payload = {
            "action": "approve",
            "feedback": "行程很满意，确认接受",
        }
        final_state = agent_2.invoke(Command(resume=resume_payload), config=config)

        # 4. 验证成功从断点恢复并流转到终态
        assert final_state["status"] == PlanStatus.APPROVED
        assert final_state["current_itinerary"] is not None


def test_agent_interrupt_and_resume_with_postgres():
    """验证：Agent 在 PostgreSQL 集中式 Checkpoint 下的跨实例挂起与唤醒恢复。"""
    from langgraph.checkpoint.postgres import PostgresSaver

    from app.core.config import get_settings

    settings = get_settings()
    if "postgresql" not in settings.DATABASE_URL:
        pytest.skip("未配置 PostgreSQL，跳过 PostgreSQL Checkpoint 专项测试")

    conn_str = settings.DATABASE_URL.replace("+psycopg", "")
    trip_id = f"trip_pg_{uuid4()}"
    config = {"configurable": {"thread_id": trip_id}}
    factory = TokyoFactsFactory()

    request = load_tokyo_trip_request()

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

    # 1. 实例 A 执行到 human_interrupt 挂起
    with PostgresSaver.from_conn_string(conn_str) as checkpointer_a:
        checkpointer_a.setup()
        agent_a = create_travel_agent_graph(factory, checkpointer=checkpointer_a)
        state_a = agent_a.invoke(initial_state, config=config)

        assert agent_a.get_state(config).next == ("human_interrupt",)
        assert state_a.get("status") == PlanStatus.AWAITING_REVIEW
        assert state_a.get("current_itinerary") is not None

    # 2. 实例 B（模拟不同 Pod 节点）从 PostgreSQL 唤醒并接收用户审阅批准
    with PostgresSaver.from_conn_string(conn_str) as checkpointer_b:
        agent_b = create_travel_agent_graph(factory, checkpointer=checkpointer_b)
        resume_payload = {"action": "approve", "feedback": "批准行程"}
        final_state = agent_b.invoke(Command(resume=resume_payload), config=config)

        assert final_state["status"] == PlanStatus.APPROVED
        assert final_state["current_itinerary"] is not None
