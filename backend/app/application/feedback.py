from uuid import UUID, uuid4

from app.application.clock import Clock
from app.application.errors import ApplicationError
from app.application.facts import FactsFactory
from app.application.models import FeedbackRecord, PlanningRunRecord, PlanningRunTrigger
from app.application.planning import start_planning
from app.application.repository import TravelRepository
from app.domain.trip import TripRequest


def _append_unique_name(values: list[str], value: str) -> None:
    """向列表追加一个不重复的名称（忽略大小写）。"""
    if value.casefold() not in {item.casefold() for item in values}:
        values.append(value)


# 把前端提交的结构化反馈操作应用到 TripRequest 上
def _apply_operations(
    request: TripRequest,
    operations: list[dict[str, object]],
) -> TripRequest:
    data = request.model_dump(mode="python")
    constraints = data["constraints"]
    for operation in operations:
        operation_name = operation["op"]
        if operation_name == "set_max_walking":
            constraints["max_walking_meters_per_day"] = operation["meters_per_day"]
        elif operation_name == "set_budget":
            constraints["total_budget"] = operation["total_budget"]
            constraints["budget_is_hard_limit"] = operation["hard_limit"]
        elif operation_name == "add_required_place":
            _append_unique_name(constraints["required_place_names"], str(operation["place_name"]))
        elif operation_name == "add_excluded_place":
            _append_unique_name(constraints["excluded_place_names"], str(operation["place_name"]))
        else:
            raise ApplicationError("UNSUPPORTED_FEEDBACK", "不支持该反馈操作", 422)
    return TripRequest.model_validate(data)


def submit_feedback(
    *,
    trip_id: UUID,
    base_plan_version: int,
    message: str,
    operations: list[dict[str, object]],
    auto_start_replanning: bool,
    repository: TravelRepository,
    clock: Clock,
    facts_factory: FactsFactory,
) -> tuple[FeedbackRecord, PlanningRunRecord | None]:
    # 校验旅行存在且版本未被其他操作抢先修改
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if trip.current_plan_version != base_plan_version:
        raise ApplicationError("VERSION_CONFLICT", "计划版本已经变化", 409)

    now = clock.now()
    # 没有可执行的结构化操作时，需要先向用户追问澄清
    requires_clarification = not operations
    feedback = FeedbackRecord(
        id=uuid4(),
        trip_id=trip.id,
        base_plan_version=base_plan_version,
        message=message,
        operations=operations,
        affected_dates=[],
        affected_activity_ids=[],
        global_scope=True,
        requires_clarification=requires_clarification,
        clarification_question=(
            "请从页面选项中明确要修改的约束" if requires_clarification else None
        ),
        planning_run_id=None,
        created_at=now,
    )
    if requires_clarification or not auto_start_replanning:
        repository.add_feedback(feedback)
        return feedback, None

    # 将反馈操作写入旅行请求，然后自动触发重新规划
    updated_request = _apply_operations(trip.request, operations)
    repository.save_trip(
        trip.model_copy(
            update={
                "request": updated_request,
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
    )
    repository.add_feedback(feedback)
    run = start_planning(
        trip_id=trip.id,
        repository=repository,
        clock=clock,
        facts_factory=facts_factory,
        trigger=PlanningRunTrigger.FEEDBACK,
        feedback_id=feedback.id,
    )
    feedback = feedback.model_copy(update={"planning_run_id": run.id})
    repository.save_feedback(feedback)
    return feedback, run
