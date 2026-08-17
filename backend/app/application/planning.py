from datetime import datetime
from uuid import UUID, uuid4

from app.application.clock import Clock
from app.application.errors import ApplicationError
from app.application.facts import FactsFactory
from app.application.models import (
    PlanningEventRecord,
    PlanningEventType,
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripStatus,
)
from app.application.repository import TravelRepository
from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.planning import DeterministicPlanner, PlannerConfig, PlanningStatus

RunStatus = PlanningRunStatus


# 向一次规划任务追加一条事件记录
def _add_event(
    repository: TravelRepository,
    *,
    run_id: UUID,
    event_type: PlanningEventType,
    message: str,
    created_at: datetime,
    step: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    sequence = len(repository.list_events(run_id)) + 1
    repository.add_event(
        PlanningEventRecord(
            id=f"{run_id}:{sequence}",
            run_id=run_id,
            sequence=sequence,
            type=event_type,
            step=step,
            message=message,
            payload=payload or {},
            created_at=created_at,
        )
    )


# 启动一次规划：创建规划任务、加载事实、调用确定性规划器并保存结果
def start_planning(
    *,
    trip_id: UUID,
    repository: TravelRepository,
    clock: Clock,
    facts_factory: FactsFactory,
    max_repair_rounds: int = 3,
    trigger: PlanningRunTrigger = PlanningRunTrigger.INITIAL,
    feedback_id: UUID | None = None,
) -> PlanningRunRecord:
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)

    now = clock.now()
    run = PlanningRunRecord(
        id=uuid4(),
        trip_id=trip.id,
        trigger=trigger,
        status=PlanningRunStatus.PLANNING,
        progress_percent=10,
        current_step="planning",
        base_plan_version=trip.current_plan_version,
        result_plan_version=None,
        feedback_id=feedback_id,
        repair_attempts=0,
        max_repair_attempts=max_repair_rounds,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=None,
    )
    repository.add_run(run)
    _add_event(
        repository,
        run_id=run.id,
        event_type=PlanningEventType.RUN_STARTED,
        message="开始生成旅行计划",
        created_at=now,
        payload={"trigger": trigger.value},
    )
    repository.save_trip(
        trip.model_copy(
            update={
                "status": TripStatus.PLANNING,
                "active_planning_run_id": run.id,
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
    )

    facts = facts_factory.build(trip.request, now)
    _add_event(
        repository,
        run_id=run.id,
        event_type=PlanningEventType.STEP_COMPLETED,
        step="facts",
        message="已加载天气、地点和路线事实",
        created_at=now,
        payload={"place_count": len(facts.places)},
    )
    # 使用确定性规划器生成行程；同一份输入会得到完全相同的输出
    outcome = DeterministicPlanner(PlannerConfig(max_repair_rounds=max_repair_rounds)).plan(facts)

    # 无可行方案时记录失败原因并抛出业务异常
    if outcome.status != PlanningStatus.FEASIBLE:
        error_details = [
            violation.model_dump(mode="json") for violation in outcome.report.violations
        ]
        failed = run.model_copy(
            update={
                "status": PlanningRunStatus.FAILED,
                "progress_percent": 100,
                "current_step": None,
                "repair_attempts": outcome.attempts,
                "error": {"code": "NO_FEASIBLE_PLAN", "violations": error_details},
                "finished_at": now,
            }
        )
        repository.save_run(failed)
        repository.save_trip(
            trip.model_copy(
                update={
                    "status": TripStatus.FAILED,
                    "active_planning_run_id": None,
                    "revision": trip.revision + 2,
                    "updated_at": now,
                }
            )
        )
        _add_event(
            repository,
            run_id=run.id,
            event_type=PlanningEventType.RUN_FAILED,
            message="当前约束下无法生成可行计划",
            created_at=now,
            payload={"violation_count": len(error_details)},
        )
        raise ApplicationError(
            "NO_FEASIBLE_PLAN",
            "当前约束下无法生成可行计划",
            422,
            details=error_details,
        )

    itinerary_data = outcome.itinerary.model_dump(mode="python")
    itinerary_data["trip_id"] = trip.id
    itinerary = Itinerary.model_validate(itinerary_data)
    # 计划版本号递增；首次生成为 1，后续在上一版基础上 +1
    parent_version = trip.current_plan_version
    version = 1 if parent_version is None else parent_version + 1

    if parent_version is not None:
        parent = repository.get_plan(trip.id, parent_version)
        if parent is not None:
            repository.save_plan(parent.model_copy(update={"status": PlanStatus.SUPERSEDED}))

    plan_trigger = (
        PlanTrigger.INITIAL if trigger == PlanningRunTrigger.INITIAL else PlanTrigger.USER_FEEDBACK
    )
    plan = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip.id,
        version=version,
        parent_version=parent_version,
        status=PlanStatus.VALID,
        itinerary=itinerary,
        constraint_report=outcome.report,
        change_summary=("生成首版行程" if parent_version is None else "根据反馈重新规划"),
        trigger=plan_trigger,
        planning_run_id=run.id,
        created_at=now,
        accepted_at=None,
    )
    repository.add_plan(plan)

    # 标记规划任务为已完成，并更新旅行状态为待确认
    completed = run.model_copy(
        update={
            "status": PlanningRunStatus.COMPLETED,
            "progress_percent": 100,
            "current_step": None,
            "result_plan_version": version,
            "repair_attempts": outcome.attempts,
            "finished_at": now,
        }
    )
    repository.save_run(completed)
    latest_trip = repository.get_trip(trip.id)
    assert latest_trip is not None
    repository.save_trip(
        latest_trip.model_copy(
            update={
                "status": TripStatus.NEEDS_REVIEW,
                "current_plan_version": version,
                "active_planning_run_id": None,
                "revision": latest_trip.revision + 1,
                "updated_at": now,
            }
        )
    )
    _add_event(
        repository,
        run_id=run.id,
        event_type=PlanningEventType.PLAN_CREATED,
        message=f"已生成计划版本 {version}",
        created_at=now,
        payload={"plan_version": version},
    )
    _add_event(
        repository,
        run_id=run.id,
        event_type=PlanningEventType.RUN_COMPLETED,
        message="旅行计划生成完成",
        created_at=now,
        payload={"plan_version": version},
    )
    return completed


# 按旅行 ID 和版本号获取计划
def get_plan(
    repository: TravelRepository,
    trip_id: UUID,
    version: int,
) -> PlanVersionRecord | None:
    return repository.get_plan(trip_id, version)


# 获取旅行的全部计划版本列表
def list_plan_versions(
    repository: TravelRepository,
    trip_id: UUID,
) -> list[PlanVersionRecord]:
    if repository.get_trip(trip_id) is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    return repository.list_plans(trip_id)


# 解析版本号：支持数字版本号或 "current" 关键字
def resolve_plan_version(
    repository: TravelRepository,
    trip_id: UUID,
    version: str,
) -> PlanVersionRecord:
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if version == "current":
        resolved_version = trip.current_plan_version
    else:
        try:
            resolved_version = int(version)
        except ValueError as exc:
            raise ApplicationError("PLAN_NOT_FOUND", "计划不存在", 404) from exc
    if resolved_version is None:
        raise ApplicationError("PLAN_NOT_FOUND", "计划不存在", 404)
    plan = repository.get_plan(trip_id, resolved_version)
    if plan is None:
        raise ApplicationError("PLAN_NOT_FOUND", "计划不存在", 404)
    return plan


# 获取某次规划任务的事件列表
def list_planning_events(
    repository: TravelRepository,
    trip_id: UUID,
    run_id: UUID,
) -> list[PlanningEventRecord]:
    if repository.get_trip(trip_id) is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if repository.get_run(trip_id, run_id) is None:
        raise ApplicationError("PLANNING_RUN_NOT_FOUND", "规划任务不存在", 404)
    return repository.list_events(run_id)


# 保存用户手动调整后的计划版本，并生成一条已完成的手动规划记录
def save_manual_plan(
    *,
    trip_id: UUID,
    base_version: int,
    itinerary: Itinerary,
    constraint_report: ConstraintReport,
    repository: TravelRepository,
    clock: Clock,
) -> tuple[PlanVersionRecord, PlanningRunRecord]:
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if trip.current_plan_version != base_version:
        raise ApplicationError("VERSION_CONFLICT", "计划版本已经变化", 409)

    now = clock.now()
    version = base_version + 1
    run = PlanningRunRecord(
        id=uuid4(),
        trip_id=trip.id,
        trigger=PlanningRunTrigger.FEEDBACK,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step=None,
        base_plan_version=base_version,
        result_plan_version=version,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=0,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    parent = repository.get_plan(trip.id, base_version)
    if parent is not None:
        repository.save_plan(parent.model_copy(update={"status": PlanStatus.SUPERSEDED}))
    plan = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip.id,
        version=version,
        parent_version=base_version,
        status=PlanStatus.VALID,
        itinerary=itinerary,
        constraint_report=constraint_report,
        change_summary="用户手动调整行程",
        trigger=PlanTrigger.MANUAL_VALIDATION,
        planning_run_id=run.id,
        created_at=now,
        accepted_at=None,
    )
    repository.add_run(run)
    repository.add_plan(plan)
    repository.save_trip(
        trip.model_copy(
            update={
                "status": TripStatus.NEEDS_REVIEW,
                "current_plan_version": version,
                "active_planning_run_id": None,
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
    )
    _add_event(
        repository,
        run_id=run.id,
        event_type=PlanningEventType.RUN_COMPLETED,
        message="手动修改版本已保存",
        created_at=now,
        payload={"plan_version": version},
    )
    return plan, run
