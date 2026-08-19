from uuid import UUID

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)
from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.domain.trip import TripRequest
from app.persistence.schema import (
    FeedbackTable,
    PlanningEventTable,
    PlanningRunTable,
    PlanVersionTable,
    TripTable,
)


def trip_to_table(record: TripRecord) -> TripTable:
    return TripTable(
        id=record.id,
        status=record.status,
        revision=record.revision,
        current_plan_version=record.current_plan_version,
        active_planning_run_id=record.active_planning_run_id,
        request_json=record.request.model_dump(mode="json"),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def table_to_trip(row: TripTable) -> TripRecord:
    return TripRecord(
        id=row.id,
        status=row.status,
        revision=row.revision,
        current_plan_version=row.current_plan_version,
        active_planning_run_id=row.active_planning_run_id,
        request=TripRequest.model_validate(row.request_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def plan_to_table(record: PlanVersionRecord) -> PlanVersionTable:
    return PlanVersionTable(
        id=record.id,
        trip_id=record.trip_id,
        version=record.version,
        parent_version=record.parent_version,
        status=record.status,
        trigger=record.trigger,
        itinerary_json=record.itinerary.model_dump(mode="json"),
        constraint_report_json=record.constraint_report.model_dump(mode="json"),
        change_summary=record.change_summary,
        planning_run_id=record.planning_run_id,
        created_at=record.created_at,
        accepted_at=record.accepted_at,
    )


def table_to_plan(row: PlanVersionTable) -> PlanVersionRecord:
    return PlanVersionRecord(
        id=row.id,
        trip_id=row.trip_id,
        version=row.version,
        parent_version=row.parent_version,
        status=row.status,
        trigger=row.trigger,
        itinerary=Itinerary.model_validate(row.itinerary_json),
        constraint_report=ConstraintReport.model_validate(row.constraint_report_json),
        change_summary=row.change_summary,
        planning_run_id=row.planning_run_id,
        created_at=row.created_at,
        accepted_at=row.accepted_at,
    )


def run_to_table(record: PlanningRunRecord) -> PlanningRunTable:
    return PlanningRunTable(
        id=record.id,
        trip_id=record.trip_id,
        trigger=record.trigger,
        status=record.status,
        progress_percent=record.progress_percent,
        current_step=record.current_step,
        base_plan_version=record.base_plan_version,
        result_plan_version=record.result_plan_version,
        feedback_id=record.feedback_id,
        repair_attempts=record.repair_attempts,
        max_repair_attempts=record.max_repair_attempts,
        error_json=record.error,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )


def table_to_run(row: PlanningRunTable) -> PlanningRunRecord:
    return PlanningRunRecord(
        id=row.id,
        trip_id=row.trip_id,
        trigger=row.trigger,
        status=row.status,
        progress_percent=row.progress_percent,
        current_step=row.current_step,
        base_plan_version=row.base_plan_version,
        result_plan_version=row.result_plan_version,
        feedback_id=row.feedback_id,
        repair_attempts=row.repair_attempts,
        max_repair_attempts=row.max_repair_attempts,
        error=row.error_json,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def event_to_table(record: PlanningEventRecord) -> PlanningEventTable:
    return PlanningEventTable(
        id=record.id,
        run_id=record.run_id,
        sequence=record.sequence,
        type=record.type,
        step=record.step,
        message=record.message,
        payload_json=record.payload,
        created_at=record.created_at,
    )


def table_to_event(row: PlanningEventTable) -> PlanningEventRecord:
    return PlanningEventRecord(
        id=row.id,
        run_id=row.run_id,
        sequence=row.sequence,
        type=row.type,
        step=row.step,
        message=row.message,
        payload=row.payload_json,
        created_at=row.created_at,
    )


def feedback_to_table(record: FeedbackRecord) -> FeedbackTable:
    return FeedbackTable(
        id=record.id,
        trip_id=record.trip_id,
        base_plan_version=record.base_plan_version,
        message=record.message,
        operations_json=record.operations,
        affected_dates_json=[d.isoformat() for d in record.affected_dates],
        affected_activity_ids_json=[str(uid) for uid in record.affected_activity_ids],
        global_scope=record.global_scope,
        requires_clarification=record.requires_clarification,
        clarification_question=record.clarification_question,
        planning_run_id=record.planning_run_id,
        created_at=record.created_at,
    )


def table_to_feedback(row: FeedbackTable) -> FeedbackRecord:
    from datetime import date

    return FeedbackRecord(
        id=row.id,
        trip_id=row.trip_id,
        base_plan_version=row.base_plan_version,
        message=row.message,
        operations=row.operations_json,
        affected_dates=[date.fromisoformat(d) for d in row.affected_dates_json],
        affected_activity_ids=[UUID(uid) for uid in row.affected_activity_ids_json],
        global_scope=row.global_scope,
        requires_clarification=row.requires_clarification,
        clarification_question=row.clarification_question,
        planning_run_id=row.planning_run_id,
        created_at=row.created_at,
    )
