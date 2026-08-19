from uuid import UUID, uuid4

from app.application.clock import Clock
from app.application.errors import ApplicationError
from app.application.facts import FactsFactory
from app.application.models import (
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
)
from app.application.planning import get_plan
from app.application.repository import TravelRepository
from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.domain.replanning import PlanDiff, ReplanningOperation
from app.planning.diff_engine import calculate_plan_diff
from app.planning.impact_analyzer import analyze_feedback_impact
from app.planning.scoped_scheduler import replan_single_day


def execute_scoped_replanning(
    *,
    trip_id: UUID,
    base_version: int,
    operations: list[ReplanningOperation],
    repository: TravelRepository,
    clock: Clock,
    facts_factory: FactsFactory,
) -> tuple[PlanVersionRecord, PlanningRunRecord, PlanDiff]:
    """应用层用例：执行局部动态重规划，生成新版本并绑定 Diff 报告。"""
    now = clock.now()
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if trip.current_plan_version != base_version:
        raise ApplicationError("VERSION_CONFLICT", "计划版本已经发生改变，请基于最新版修改", 409)

    base_plan = get_plan(repository, trip_id, base_version)
    if base_plan is None:
        raise ApplicationError("PLAN_NOT_FOUND", "基础计划版本不存在", 404)

    # 影响分析
    impact = analyze_feedback_impact(operations, base_plan.itinerary)
    facts = facts_factory.build(trip.request, now)

    # 提取需要屏蔽和替换的地点
    blocked_places: set[str] = set()
    replacements: dict[str, str] = {}
    time_window_adjusts: dict = {}

    for op in operations:
        if hasattr(op, "place_name") and op.op == "remove_place":
            blocked_places.add(op.place_name.casefold())
        elif hasattr(op, "original_place_name") and op.op == "replace_place":
            replacements[op.original_place_name.casefold()] = op.replacement_place_name
        elif op.op == "adjust_day_time_window":
            time_window_adjusts[op.day] = (op.start_time, op.end_time)

    # 逐日重排：受影响天执行局部重调度，未受影响天 100% 冻结保留
    new_days = []
    for day in base_plan.itinerary.days:
        if day.date in impact.affected_dates:
            tw = time_window_adjusts.get(day.date, (None, None))
            repaired_day = replan_single_day(
                original_day=day,
                request=trip.request,
                available_places=facts.places,
                route_matrix=facts.route_matrix,
                blocked_place_names=blocked_places,
                replacement_place_names=replacements,
                start_time_override=tw[0],
                end_time_override=tw[1],
            )
            new_days.append(repaired_day)
        else:
            # 零扰动保留未受波及日
            new_days.append(day)

    # 组装新行程聚合根
    new_itinerary = base_plan.itinerary.model_copy(
        update={
            "days": new_days,
            "generated_at": now,
            "general_notes": base_plan.itinerary.general_notes
            + [f"由局部重规划生成 (基于 v{base_version})"],
        }
    )

    # 全局硬约束二次审计
    engine = create_default_engine()
    context = ConstraintContext(
        request=trip.request,
        places_by_id={p.id: p for p in facts.places},
        checked_at=now,
    )
    report = engine.check(new_itinerary, context)

    # 计算语义 Diff
    new_version_num = base_version + 1
    diff = calculate_plan_diff(
        old_plan=base_plan.itinerary,
        new_plan=new_itinerary,
        from_version=base_version,
        to_version=new_version_num,
    )

    # 派生落盘新版本与任务记录
    run_id = uuid4()
    plan_record = PlanVersionRecord(
        id=uuid4(),
        trip_id=trip_id,
        version=new_version_num,
        parent_version=base_version,
        status=PlanStatus.VALID if report.passed else PlanStatus.DRAFT,
        trigger=PlanTrigger.USER_FEEDBACK,
        itinerary=new_itinerary,
        constraint_report=report,
        change_summary=diff.human_summary,
        planning_run_id=run_id,
        created_at=now,
    )

    run_record = PlanningRunRecord(
        id=run_id,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.FEEDBACK,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=base_version,
        result_plan_version=new_version_num,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )

    # 保存版本与更新旅行当前指针
    repository.add_plan(plan_record)
    repository.add_run(run_record)
    repository.save_trip(
        trip.model_copy(
            update={
                "current_plan_version": new_version_num,
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
    )

    return plan_record, run_record, diff
