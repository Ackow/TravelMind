from uuid import UUID

from fastapi import APIRouter, status
from pydantic import Field

from app.api.dependencies import ClockDep, FactsFactoryDep, RepositoryDep
from app.api.schemas import ApiModel, CurrentPlanResponse, PlanningRunResponse
from app.application.replanning import execute_scoped_replanning
from app.domain.replanning import PlanDiff, ReplanningOperation

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/replanning-runs",
    tags=["replanning"],
)


class ScopedReplanningRequest(ApiModel):
    base_plan_version: int = Field(ge=1)
    operations: list[ReplanningOperation] = Field(min_length=1)


class ScopedReplanningResponse(ApiModel):
    plan: CurrentPlanResponse
    planning_run: PlanningRunResponse
    diff: PlanDiff


@router.post(
    "",
    response_model=ScopedReplanningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="触发结构化局部重规划",
)
def create_scoped_replanning(
    trip_id: UUID,
    payload: ScopedReplanningRequest,
    repository: RepositoryDep,
    clock: ClockDep,
    facts_factory: FactsFactoryDep,
) -> ScopedReplanningResponse:
    """接收结构化重规划操作，执行局部重排，返回新计划版本及 Diff。"""
    plan, run, diff = execute_scoped_replanning(
        trip_id=trip_id,
        base_version=payload.base_plan_version,
        operations=payload.operations,
        repository=repository,
        clock=clock,
        facts_factory=facts_factory,
    )

    return ScopedReplanningResponse(
        plan=CurrentPlanResponse.model_validate(plan.model_dump(mode="python")),
        planning_run=PlanningRunResponse.model_validate(run.model_dump(mode="python")),
        diff=diff,
    )
