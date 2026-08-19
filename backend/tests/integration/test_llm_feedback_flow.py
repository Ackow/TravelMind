from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.agent.feedback_parser import ParsedFeedback, SetMaxWalkingOp
from app.agent.llm_client import FakeLLMClient
from app.application.clock import FixedClock
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.memory_repository import InMemoryTravelRepository
from app.main import create_app


def test_natural_language_feedback_triggers_llm_and_creates_v2() -> None:
    # 准备 Fake LLM 返回解析操作
    fake_llm = FakeLLMClient(
        [
            ParsedFeedback(
                summary="将每日步行限制为 2 公里",
                operations=[
                    SetMaxWalkingOp(op="set_max_walking", meters_per_day=2000, reason="用户反馈")
                ],
                affected_day_indices=[],
                requires_clarification=False,
            )
        ]
    )

    app = create_app(
        repository=InMemoryTravelRepository(),
        clock=FixedClock(datetime(2026, 10, 1, 8, 0, tzinfo=UTC)),
    )
    # 将 fake_llm 挂载到应用上下文
    app.state.llm_client = fake_llm

    client = TestClient(app)

    # 1. 创建旅行
    trip = client.post(
        "/api/v1/trips", json=load_tokyo_trip_request().model_dump(mode="json")
    ).json()
    base_url = f"/api/v1/trips/{trip['id']}"

    # 2. 生成版本 1
    client.post(f"{base_url}/planning-runs")

    # 3. 提交自然语言文本（不带 client_operations）
    res = client.post(
        f"{base_url}/feedback",
        json={
            "base_plan_version": 1,
            "message": "走不动了，希望每天步行控制在两公里以内",
            "auto_start_replanning": True,
        },
    )

    assert res.status_code == 202
    run = res.json()["planning_run"]
    assert run["result_plan_version"] == 2

    # 4. 验证版本 2 的步行约束生效
    v2_plan = client.get(f"{base_url}/plans/2").json()
    assert v2_plan["version"] == 2
    assert all(day["statistics"]["walking_meters"] <= 2000 for day in v2_plan["itinerary"]["days"])
