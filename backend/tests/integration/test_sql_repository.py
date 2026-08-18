from datetime import date, datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.errors import ApplicationError
from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningEventType,
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripRecord,
    TripStatus,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.domain.constraints import ConstraintReport
from app.domain.itinerary import BudgetSummary
from app.domain.common import Money
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.tokyo_facts_factory import TokyoFactsFactory
from app.planning.planner import build_itinerary
from app.infrastructure.sql_repository import SqlAlchemyTravelRepository
from app.main import create_app
from app.persistence.base import Base


@pytest.fixture
def sqlite_repo(tmp_path):
    """创建临时独立 SQLite 数据库仓储。"""
    db_file = tmp_path / "test_travelmind.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine)
    return SqlAlchemyTravelRepository(session_factory)


@pytest.fixture
def postgres_repo():
    """使用 Docker 中运行的 PostgreSQL 16 数据库仓储。"""
    settings = get_settings()
    try:
        Base.metadata.create_all(engine)
        return SqlAlchemyTravelRepository(SessionLocal)
    except Exception as exc:
        pytest.skip(f"PostgreSQL 连接不可用，跳过 PostgreSQL 专项测试: {exc}")


def test_trip_crud_and_optimistic_locking(sqlite_repo):
    """验证旅行记录 CRUD 与乐观并发锁保护 (SQLite)。"""
    now = datetime.now(timezone.utc)
    trip_id = uuid4()
    trip = TripRecord(
        id=trip_id,
        status=TripStatus.DRAFT,
        revision=1,
        request=load_tokyo_trip_request(),
        created_at=now,
        updated_at=now,
    )

    # 1. 新增与查询
    sqlite_repo.add_trip(trip)
    fetched = sqlite_repo.get_trip(trip_id)
    assert fetched is not None
    assert fetched.id == trip_id
    assert fetched.revision == 1

    # 2. 正常版本自增更新
    updated = fetched.model_copy(update={"revision": 2, "status": TripStatus.PLANNING})
    sqlite_repo.save_trip(updated)

    refetched = sqlite_repo.get_trip(trip_id)
    assert refetched.revision == 2
    assert refetched.status == TripStatus.PLANNING

    # 3. 并发冲突尝试：以陈旧版本 (revision=1) 尝试覆盖
    stale_update = fetched.model_copy(update={"status": TripStatus.FAILED})
    with pytest.raises(ApplicationError) as exc_info:
        sqlite_repo.save_trip(stale_update)
    assert exc_info.value.code == "CONCURRENCY_CONFLICT"
    assert exc_info.value.status_code == 409


def test_plan_versions_and_runs_lifecycle(postgres_repo):
    """验证在 PostgreSQL 中的多版本计划与规划任务完整生命周期。"""
    now = datetime.now(timezone.utc)
    trip_id = uuid4()
    trip = TripRecord(
        id=trip_id,
        status=TripStatus.PLANNING,
        revision=1,
        request=load_tokyo_trip_request(),
        created_at=now,
        updated_at=now,
    )
    postgres_repo.add_trip(trip)

    # 1. 创建任务记录
    run_id = uuid4()
    run = PlanningRunRecord(
        id=run_id,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.INITIAL,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=None,
        result_plan_version=1,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    postgres_repo.add_run(run)

    # 2. 创建 v1 计划版本
    itinerary = build_itinerary(TokyoFactsFactory().build(trip.request, now))
    v1_plan = PlanVersionRecord(
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
        change_summary="初始版本",
        planning_run_id=run_id,
        created_at=now,
    )
    postgres_repo.add_plan(v1_plan)

    # 3. 创建 v2 派生版本
    v2_plan = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=2,
        parent_version=1,
        status=PlanStatus.VALID,
        trigger=PlanTrigger.USER_FEEDBACK,
        itinerary=itinerary,
        constraint_report=ConstraintReport(
            passed=True,
            violations=[],
            checked_rule_codes=[],
            checked_at=now,
            engine_version="1.0.0",
        ),
        change_summary="局部重排",
        planning_run_id=run_id,
        created_at=now,
    )
    postgres_repo.add_plan(v2_plan)

    # 4. 验证版本列表查询
    plans = postgres_repo.list_plans(trip_id)
    assert len(plans) == 2
    assert [p.version for p in plans] == [1, 2]
    assert plans[1].parent_version == 1

    # 5. 验证事件流记录与时序
    event_1 = PlanningEventRecord(
        id=str(uuid4()),
        run_id=run_id,
        sequence=1,
        type=PlanningEventType.RUN_STARTED,
        step="research",
        message="开始事实检索",
        payload={"places_count": 10},
        created_at=now,
    )
    event_2 = PlanningEventRecord(
        id=str(uuid4()),
        run_id=run_id,
        sequence=2,
        type=PlanningEventType.RUN_COMPLETED,
        step="completed",
        message="规划完成",
        payload={},
        created_at=now,
    )
    postgres_repo.add_event(event_1)
    postgres_repo.add_event(event_2)

    events = postgres_repo.list_events(run_id)
    assert len(events) == 2
    assert events[0].sequence == 1
    assert events[1].sequence == 2


def test_fastapi_e2e_with_postgresql_repository(postgres_repo):
    """端到端验证：FastAPI 搭载 PostgreSQL 仓储执行完整的旅行创建与规划流程。"""
    app = create_app(repository=postgres_repo)
    client = TestClient(app)

    # 1. 创建旅行
    trip_resp = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    )
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    trip_id = trip_data["id"]

    # 2. 触发确定性规划 (FastAPI 异步规划响应 202 Accepted)
    plan_run_resp = client.post(f"/api/v1/trips/{trip_id}/planning-runs")
    assert plan_run_resp.status_code == 202

    # 3. 从 PostgreSQL 查询生成的计划
    get_plan_resp = client.get(f"/api/v1/trips/{trip_id}/plans/1")
    assert get_plan_resp.status_code == 200
    plan_body = get_plan_resp.json()
    assert plan_body["version"] == 1
    assert len(plan_body["itinerary"]["days"]) > 0


def test_version_history_and_checkout(postgres_repo):
    """验证版本谱系追踪与计划版本检出回滚服务。"""
    from app.application.versioning import checkout_plan_version, get_plan_history

    now = datetime.now(timezone.utc)
    trip_id = uuid4()
    trip = TripRecord(
        id=trip_id,
        status=TripStatus.PLANNING,
        revision=1,
        request=load_tokyo_trip_request(),
        created_at=now,
        updated_at=now,
    )
    postgres_repo.add_trip(trip)

    run_id = uuid4()
    run = PlanningRunRecord(
        id=run_id,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.INITIAL,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=None,
        result_plan_version=1,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    postgres_repo.add_run(run)

    itinerary = build_itinerary(TokyoFactsFactory().build(trip.request, now))
    report = ConstraintReport(
        passed=True,
        violations=[],
        checked_rule_codes=[],
        checked_at=now,
        engine_version="1.0.0",
    )

    v1 = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=1,
        parent_version=None,
        status=PlanStatus.VALID,
        trigger=PlanTrigger.INITIAL,
        itinerary=itinerary,
        constraint_report=report,
        change_summary="v1 初始版",
        planning_run_id=run_id,
        created_at=now,
    )
    v2 = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=2,
        parent_version=1,
        status=PlanStatus.VALID,
        trigger=PlanTrigger.USER_FEEDBACK,
        itinerary=itinerary,
        constraint_report=report,
        change_summary="v2 用户反馈版",
        planning_run_id=run_id,
        created_at=now,
    )
    postgres_repo.add_plan(v1)
    postgres_repo.add_plan(v2)

    # 1. 验证获取版本历史
    history = get_plan_history(postgres_repo, trip_id)
    assert len(history) == 2
    assert [p.version for p in history] == [1, 2]

    # 2. 检出并回滚至 v1 版本
    updated_trip = checkout_plan_version(postgres_repo, trip_id, target_version=1)
    assert updated_trip.current_plan_version == 1
    assert updated_trip.revision == 2

    # 3. 验证数据库中已持久化更新
    refetched = postgres_repo.get_trip(trip_id)
    assert refetched.current_plan_version == 1
    assert refetched.revision == 2
