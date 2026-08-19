from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import ClockDep, RepositoryDep
from app.api.schemas import CurrentPlanResponse, PlanListResponse, PlanVersionSummary, TripResponse
from app.api.v1.trips import to_trip_response
from app.application.errors import ApplicationError
from app.application.models import PlanStatus, TripStatus
from app.application.planning import list_plan_versions as list_plan_versions_use_case
from app.application.planning import resolve_plan_version
from app.application.versioning import checkout_plan_version

router = APIRouter(prefix="/api/v1/trips/{trip_id}/plans", tags=["plans"])


@router.get(
    "",
    response_model=PlanListResponse,
    operation_id="list_plan_versions",
)
def list_plan_versions(
    trip_id: UUID,
    repository: RepositoryDep,
) -> PlanListResponse:
    plans = list_plan_versions_use_case(repository, trip_id)
    return PlanListResponse(
        items=[
            PlanVersionSummary(
                id=plan.id,
                trip_id=plan.trip_id,
                version=plan.version,
                parent_version=plan.parent_version,
                status=plan.status,
                day_count=len(plan.itinerary.days),
                planned_total=plan.itinerary.budget.planned_total,
                error_count=sum(
                    violation.severity.value == "error"
                    for violation in plan.constraint_report.violations
                ),
                warning_count=sum(
                    violation.severity.value == "warning"
                    for violation in plan.constraint_report.violations
                ),
                change_summary=plan.change_summary,
                trigger=plan.trigger,
                planning_run_id=plan.planning_run_id,
                created_at=plan.created_at,
            )
            for plan in plans
        ]
    )


@router.get(
    "/{version}",
    response_model=CurrentPlanResponse,
    operation_id="get_plan_version",
)
def get_plan_endpoint(
    trip_id: UUID,
    version: str,
    repository: RepositoryDep,
) -> CurrentPlanResponse:
    plan = resolve_plan_version(repository, trip_id, version)
    return CurrentPlanResponse.model_validate(plan.model_dump(mode="python"))


@router.post(
    "/{version}/accept",
    response_model=CurrentPlanResponse,
    operation_id="accept_plan_version",
)
def accept_plan_endpoint(
    trip_id: UUID,
    version: int,
    repository: RepositoryDep,
    clock: ClockDep,
) -> CurrentPlanResponse:
    """确认并接受指定的计划版本，将计划置为 accepted，旅行置为 completed。"""
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    plan = repository.get_plan(trip_id, version)
    if plan is None:
        raise ApplicationError("PLAN_NOT_FOUND", f"计划版本 v{version} 不存在", 404)

    now = clock.now()
    updated_plan = plan.model_copy(
        update={
            "status": PlanStatus.ACCEPTED,
            "accepted_at": now,
        }
    )
    repository.save_plan(updated_plan)

    updated_trip = trip.model_copy(
        update={
            "status": TripStatus.COMPLETED,
            "current_plan_version": version,
            "revision": trip.revision + 1,
            "updated_at": now,
        }
    )
    repository.save_trip(updated_trip)
    return CurrentPlanResponse.model_validate(updated_plan.model_dump(mode="python"))


@router.post(
    "/{version}/checkout",
    response_model=TripResponse,
    operation_id="checkout_plan_version",
)
def checkout_plan_endpoint(
    trip_id: UUID,
    version: int,
    repository: RepositoryDep,
) -> TripResponse:
    """检出/切换当前旅行生效的计划版本。"""
    updated_trip = checkout_plan_version(repository, trip_id, target_version=version)
    return to_trip_response(updated_trip)

