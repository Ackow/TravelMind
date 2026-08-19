from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import ClockDep, FactsFactoryDep, RepositoryDep
from app.api.schemas import (
    CurrentPlanResponse,
    ManualPlanEditRequest,
    ManualPlanEditResponse,
    PlanningRunResponse,
)
from app.application.manual_edits import apply_manual_edits

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/manual-edits",
    tags=["plans"],
)


@router.post(
    "",
    response_model=ManualPlanEditResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_manual_plan_edit",
)
def create_manual_plan_edit(
    trip_id: UUID,
    payload: ManualPlanEditRequest,
    repository: RepositoryDep,
    clock: ClockDep,
    facts_factory: FactsFactoryDep,
) -> ManualPlanEditResponse:
    plan, run = apply_manual_edits(
        trip_id=trip_id,
        base_version=payload.base_plan_version,
        day_edits=[item.model_dump(mode="python") for item in payload.days],
        repository=repository,
        clock=clock,
        facts_factory=facts_factory,
    )

    return ManualPlanEditResponse(
        plan=CurrentPlanResponse.model_validate(plan.model_dump(mode="python")),
        planning_run=PlanningRunResponse.model_validate(run.model_dump(mode="python")),
    )
