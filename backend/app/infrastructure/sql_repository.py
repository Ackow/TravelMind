from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.errors import ApplicationError
from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)
from app.application.repository import TravelRepository
from app.persistence.converters import (
    event_to_table,
    feedback_to_table,
    plan_to_table,
    run_to_table,
    table_to_event,
    table_to_feedback,
    table_to_plan,
    table_to_run,
    table_to_trip,
    trip_to_table,
)
from app.persistence.schema import (
    FeedbackTable,
    PlanningEventTable,
    PlanningRunTable,
    PlanVersionTable,
    TripTable,
)


class SqlAlchemyTravelRepository(TravelRepository):
    """基于 SQLAlchemy 2.0 的生产级关系型数据库仓储实现。"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def add_trip(self, trip: TripRecord) -> None:
        with self._session_factory() as session:
            existing = session.get(TripTable, trip.id)
            if existing is not None:
                raise ValueError("trip already exists")
            row = trip_to_table(trip)
            session.add(row)
            session.commit()

    def get_trip(self, trip_id: UUID) -> TripRecord | None:
        with self._session_factory() as session:
            row = session.get(TripTable, trip_id)
            return None if row is None else table_to_trip(row)

    def save_trip(self, trip: TripRecord) -> None:
        """带乐观锁保护的保存操作"""
        with self._session_factory() as session:
            row = session.get(TripTable, trip.id)
            if row is None:
                raise ValueError("trip does not exist")
            
            # 乐观锁校验：如果传入版本号与数据库不一致，抛出版本冲突
            if row.revision >= trip.revision:
                raise ApplicationError(
                    "CONCURRENCY_CONFLICT",
                    f"旅行状态已被其他操作更新 (当前版本: {row.revision}, 提交版本: {trip.revision})",
                    409,
                )
            
            row.status = trip.status
            row.revision = trip.revision
            row.current_plan_version = trip.current_plan_version
            row.active_planning_run_id = trip.active_planning_run_id
            row.request_json = trip.request.model_dump(mode="json")
            row.updated_at = trip.updated_at
            session.commit()

    def add_run(self, run: PlanningRunRecord) -> None:
        with self._session_factory() as session:
            existing = session.get(PlanningRunTable, run.id)
            if existing is not None:
                raise ValueError("planning run already exists")
            session.add(run_to_table(run))
            session.commit()

    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord | None:
        with self._session_factory() as session:
            stmt = select(PlanningRunTable).where(
                PlanningRunTable.id == run_id,
                PlanningRunTable.trip_id == trip_id,
            )
            row = session.scalars(stmt).first()
            return None if row is None else table_to_run(row)

    def save_run(self, run: PlanningRunRecord) -> None:
        with self._session_factory() as session:
            row = session.get(PlanningRunTable, run.id)
            if row is None:
                raise ValueError("planning run does not exist")
            row.status = run.status
            row.progress_percent = run.progress_percent
            row.current_step = run.current_step
            row.result_plan_version = run.result_plan_version
            row.repair_attempts = run.repair_attempts
            row.error_json = run.error
            row.finished_at = run.finished_at
            session.commit()

    def add_plan(self, plan: PlanVersionRecord) -> None:
        with self._session_factory() as session:
            stmt = select(PlanVersionTable).where(
                PlanVersionTable.trip_id == plan.trip_id,
                PlanVersionTable.version == plan.version,
            )
            if session.scalars(stmt).first() is not None:
                raise ValueError("plan version already exists")
            session.add(plan_to_table(plan))
            session.commit()

    def save_plan(self, plan: PlanVersionRecord) -> None:
        with self._session_factory() as session:
            stmt = select(PlanVersionTable).where(
                PlanVersionTable.trip_id == plan.trip_id,
                PlanVersionTable.version == plan.version,
            )
            row = session.scalars(stmt).first()
            if row is None:
                raise ValueError("plan version does not exist")
            row.status = plan.status
            row.itinerary_json = plan.itinerary.model_dump(mode="json")
            row.constraint_report_json = plan.constraint_report.model_dump(mode="json")
            row.change_summary = plan.change_summary
            row.accepted_at = plan.accepted_at
            session.commit()

    def get_plan(self, trip_id: UUID, version: int) -> PlanVersionRecord | None:
        with self._session_factory() as session:
            stmt = select(PlanVersionTable).where(
                PlanVersionTable.trip_id == trip_id,
                PlanVersionTable.version == version,
            )
            row = session.scalars(stmt).first()
            return None if row is None else table_to_plan(row)

    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]:
        with self._session_factory() as session:
            stmt = (
                select(PlanVersionTable)
                .where(PlanVersionTable.trip_id == trip_id)
                .order_by(PlanVersionTable.version.asc())
            )
            rows = session.scalars(stmt).all()
            return [table_to_plan(r) for r in rows]

    def add_event(self, event: PlanningEventRecord) -> None:
        with self._session_factory() as session:
            session.add(event_to_table(event))
            session.commit()

    def list_events(self, run_id: UUID) -> list[PlanningEventRecord]:
        with self._session_factory() as session:
            stmt = (
                select(PlanningEventTable)
                .where(PlanningEventTable.run_id == run_id)
                .order_by(PlanningEventTable.sequence.asc())
            )
            rows = session.scalars(stmt).all()
            return [table_to_event(r) for r in rows]

    def add_feedback(self, feedback: FeedbackRecord) -> None:
        with self._session_factory() as session:
            session.add(feedback_to_table(feedback))
            session.commit()

    def save_feedback(self, feedback: FeedbackRecord) -> None:
        with self._session_factory() as session:
            row = session.get(FeedbackTable, feedback.id)
            if row is None:
                raise ValueError("feedback does not exist")
            row.requires_clarification = feedback.requires_clarification
            row.clarification_question = feedback.clarification_question
            session.commit()