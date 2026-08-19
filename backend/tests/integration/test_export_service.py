from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.application.export_service import ExportService
from app.application.models import (
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripRecord,
    TripStatus,
)
from app.domain.constraints import ConstraintReport
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.memory_repository import InMemoryTravelRepository
from app.infrastructure.tokyo_facts_factory import TokyoFactsFactory
from app.main import create_app
from app.planning.planner import build_itinerary


def test_export_markdown_completeness():
    """验证：导出服务生成的 Markdown 文档结构完整、金额准确、包含逐日日程与注意事项。"""
    repo = InMemoryTravelRepository()
    export_service = ExportService(repo)
    now = datetime.now(UTC)

    # 1. 构造旅行与计划数据
    trip_id = uuid4()
    request = load_tokyo_trip_request()
    trip = TripRecord(
        id=trip_id,
        status=TripStatus.COMPLETED,
        revision=1,
        current_plan_version=1,
        request=request,
        created_at=now,
        updated_at=now,
    )
    repo.add_trip(trip)

    itinerary = build_itinerary(TokyoFactsFactory().build(request, now))
    plan = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=1,
        parent_version=None,
        status=PlanStatus.VALID,
        trigger=PlanTrigger.INITIAL,
        itinerary=itinerary,
        constraint_report=ConstraintReport(
            passed=True,
            violations=[],
            checked_rule_codes=[],
            checked_at=now,
            engine_version="1.0.0",
        ),
        change_summary="初始生成",
        planning_run_id=uuid4(),
        created_at=now,
    )
    repo.add_plan(plan)

    # 2. 执行导出
    markdown_text = export_service.export_to_markdown(trip_id, version=1)

    # 3. 校验导出文本的关键要素
    assert f"# ✈️ {request.destination} 旅行路书方案" in markdown_text
    assert "## 1. 旅行概览" in markdown_text
    assert "## 2. 逐日详细行程表" in markdown_text
    assert "## 3. 费用预算明细汇总" in markdown_text
    assert "## 4. 出行前安全与注意事项" in markdown_text
    assert "第 1 天" in markdown_text


def test_export_markdown_endpoint():
    """验证：GET /api/v1/trips/{trip_id}/export/markdown 接口端点成功返回 text/markdown。"""
    repo = InMemoryTravelRepository()
    now = datetime.now(UTC)
    trip_id = uuid4()
    request = load_tokyo_trip_request()
    trip = TripRecord(
        id=trip_id,
        status=TripStatus.COMPLETED,
        revision=1,
        current_plan_version=1,
        request=request,
        created_at=now,
        updated_at=now,
    )
    repo.add_trip(trip)

    itinerary = build_itinerary(TokyoFactsFactory().build(request, now))
    plan = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=1,
        parent_version=None,
        status=PlanStatus.VALID,
        trigger=PlanTrigger.INITIAL,
        itinerary=itinerary,
        constraint_report=ConstraintReport(
            passed=True,
            violations=[],
            checked_rule_codes=[],
            checked_at=now,
            engine_version="1.0.0",
        ),
        change_summary="初始生成",
        planning_run_id=uuid4(),
        created_at=now,
    )
    repo.add_plan(plan)

    app = create_app(repository=repo)
    client = TestClient(app)

    response = client.get(f"/api/v1/trips/{trip_id}/export/markdown")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert f"# ✈️ {request.destination} 旅行路书方案" in response.text
