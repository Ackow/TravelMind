from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.application.models import (
    PlanningRunStatus,
    PlanStatus,
    PlanTrigger,
    TripStatus,
)
from app.persistence.base import Base, utc_now


class TripTable(Base):
    """旅行聚合根记录表"""

    __tablename__ = "trips"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TripStatus.DRAFT)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 乐观并发锁
    current_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_planning_run_id: Mapped[UUID | None] = mapped_column(nullable=True)

    # 原始请求参数以 JSON 存储保证向后兼容
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # 关联子表
    plans: Mapped[list["PlanVersionTable"]] = relationship(
        "PlanVersionTable", back_populates="trip", cascade="all, delete-orphan"
    )
    runs: Mapped[list["PlanningRunTable"]] = relationship(
        "PlanningRunTable", back_populates="trip", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["FeedbackTable"]] = relationship(
        "FeedbackTable", back_populates="trip", cascade="all, delete-orphan"
    )


class PlanVersionTable(Base):
    """计划版本不可变快照表"""

    __tablename__ = "plan_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PlanStatus.VALID)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False, default=PlanTrigger.INITIAL)

    # 不可变 JSON 结构快照
    itinerary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    constraint_report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    planning_run_id: Mapped[UUID] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关系与复合唯一索引
    trip: Mapped["TripTable"] = relationship("TripTable", back_populates="plans")

    __table_args__ = (UniqueConstraint("trip_id", "version", name="uq_trip_plan_version"),)


class PlanningRunTable(Base):
    """规划运行任务审计表"""

    __tablename__ = "planning_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PlanningRunStatus.QUEUED
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    base_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_id: Mapped[UUID | None] = mapped_column(nullable=True)

    repair_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_repair_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trip: Mapped["TripTable"] = relationship("TripTable", back_populates="runs")
    events: Mapped[list["PlanningEventTable"]] = relationship(
        "PlanningEventTable", back_populates="run", cascade="all, delete-orphan"
    )


class PlanningEventTable(Base):
    """规划过程 Trace 事件流表"""

    __tablename__ = "planning_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("planning_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    run: Mapped["PlanningRunTable"] = relationship("PlanningRunTable", back_populates="events")

    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),)


class FeedbackTable(Base):
    """用户交互反馈记录表"""

    __tablename__ = "user_feedbacks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    operations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_dates_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_activity_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    global_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_clarification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    planning_run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    trip: Mapped["TripTable"] = relationship("TripTable", back_populates="feedbacks")


class ToolCallTable(Base):
    """真实外部工具调用审计表"""

    __tablename__ = "tool_calls"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
