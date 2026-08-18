from uuid import UUID
from fastapi import APIRouter, status
from app.api.dependencies import ClockDep, FactsFactoryDep, RepositoryDep
from app.api.schemas import (
    PlanningEventListResponse,
    PlanningEventResponse,
    PlanningRunResponse,
    StartPlanningResponse,
)
from app.application.planning import list_planning_events as list_planning_events_use_case
from app.application.planning import start_planning

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/planning-runs",
    tags=["planning"],
)


@router.post(
    "",
    response_model=StartPlanningResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="start_planning_run",
)
def start_planning_endpoint(
    trip_id: UUID,
    repository: RepositoryDep,
    clock: ClockDep,
    facts_factory: FactsFactoryDep,
) -> StartPlanningResponse:
    run = start_planning(
        trip_id=trip_id,
        repository=repository,
        clock=clock,
        facts_factory=facts_factory,
    )

    return StartPlanningResponse(
        planning_run=PlanningRunResponse.model_validate(run.model_dump(mode="python")),
        events_url=f"/api/v1/trips/{trip_id}/planning-runs/{run.id}/events",
    )


@router.get(
    "/{run_id}/events",
    response_model=PlanningEventListResponse,
    operation_id="list_planning_events",
)
def list_planning_events(
    trip_id: UUID,
    run_id: UUID,
    repository: RepositoryDep,
) -> PlanningEventListResponse:
    events = list_planning_events_use_case(repository, trip_id, run_id)
    return PlanningEventListResponse(
        items=[
            PlanningEventResponse.model_validate(event.model_dump(mode="python"))
            for event in events
        ]
    )
