from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import ClockDep, FactsFactoryDep, RepositoryDep
from app.api.schemas import (
    FeedbackCreateRequest,
    FeedbackRecordResponse,
    FeedbackResponse,
    FeedbackScope,
    PlanningRunResponse,
)
from app.application.feedback import submit_feedback

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/feedback",
    tags=["feedback"],
)


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="create_feedback",
)
def create_feedback_endpoint(
    trip_id: UUID,
    payload: FeedbackCreateRequest,
    response: Response,
    repository: RepositoryDep,
    clock: ClockDep,
    facts_factory: FactsFactoryDep,
) -> FeedbackResponse:
    """保存结构化反馈，并按需启动下一版规划。

    如果反馈缺少明确操作，则返回 200 并要求用户澄清；
    否则正常返回 202 和可选的重新规划任务。
    """

    feedback, run = submit_feedback(
        trip_id=trip_id,
        base_plan_version=payload.base_plan_version,
        message=payload.message,
        operations=[item.model_dump(mode="python") for item in payload.client_operations],
        auto_start_replanning=payload.auto_start_replanning,
        repository=repository,
        clock=clock,
        facts_factory=facts_factory,
    )

    if feedback.requires_clarification:
        response.status_code = status.HTTP_200_OK

    return FeedbackResponse(
        feedback=FeedbackRecordResponse(
            id=feedback.id,
            trip_id=feedback.trip_id,
            base_plan_version=feedback.base_plan_version,
            message=feedback.message,
            operations=feedback.operations,
            scope=FeedbackScope(),
            requires_clarification=feedback.requires_clarification,
            clarification_question=feedback.clarification_question,
            planning_run_id=feedback.planning_run_id,
            created_at=feedback.created_at,
        ),
        planning_run=(
            None
            if run is None
            else PlanningRunResponse.model_validate(run.model_dump(mode="python"))
        ),
        events_url=(
            None if run is None else f"/api/v1/trips/{trip_id}/planning-runs/{run.id}/events"
        ),
    )
