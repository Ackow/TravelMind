from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import RepositoryDep
from app.api.schemas import CurrentPlanResponse, PlanListResponse, PlanVersionSummary
from app.application.planning import list_plan_versions as list_plan_versions_use_case
from app.application.planning import resolve_plan_version

router = APIRouter(prefix="/api/v1/trips/{trip_id}/plans", tags=["plans"])


@router.get(
    "",
    response_model=PlanListResponse,
    operation_id="list_plan_versions",
)
# 获取某次旅行的全部计划版本摘要
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
# 获取指定版本（或 current）的完整计划详情
def get_plan_endpoint(
    trip_id: UUID,
    version: str,
    repository: RepositoryDep,
) -> CurrentPlanResponse:
    plan = resolve_plan_version(repository, trip_id, version)
    return CurrentPlanResponse.model_validate(plan.model_dump(mode="python"))
