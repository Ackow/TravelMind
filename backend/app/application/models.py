from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.domain.trip import TripRequest


class ApplicationModel(BaseModel):
    """应用层记录也禁止悄悄接受未知字段。"""

    model_config = ConfigDict(extra="forbid")


# 旅行生命周期状态
class TripStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    NEEDS_REVIEW = "needs_review"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


# 规划任务运行状态
class PlanningRunStatus(StrEnum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    PLANNING = "planning"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    WAITING_FOR_REVIEW = "waiting_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanningRunTrigger(StrEnum):
    INITIAL = "initial"
    FEEDBACK = "feedback"
    DATA_CHANGE = "data_change"


# 计划版本状态
class PlanStatus(StrEnum):
    DRAFT = "draft"
    VALID = "valid"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


class PlanTrigger(StrEnum):
    INITIAL = "initial"
    USER_FEEDBACK = "user_feedback"
    DATA_CHANGE = "data_change"
    MANUAL_VALIDATION = "manual_validation"


class PlanningEventType(StrEnum):
    RUN_STARTED = "run_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    CONSTRAINT_FOUND = "constraint_found"
    REPAIR_STARTED = "repair_started"
    PLAN_CREATED = "plan_created"
    REVIEW_REQUIRED = "review_required"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class TripRecord(ApplicationModel):
    id: UUID  # 旅行唯一 ID
    status: TripStatus  # 旅行状态
    revision: int = Field(ge=1)  # 版本号（乐观锁）
    request: TripRequest  # 用户旅行请求
    current_plan_version: int | None = None  # 当前生效的计划版本
    active_planning_run_id: UUID | None = None  # 正在执行的规划任务 ID
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间


class PlanningRunRecord(ApplicationModel):
    id: UUID  # 规划任务唯一 ID
    trip_id: UUID  # 所属旅行 ID
    trigger: PlanningRunTrigger  # 触发来源
    status: PlanningRunStatus  # 运行状态
    progress_percent: int = Field(ge=0, le=100)  # 进度百分比
    current_step: str | None = None  # 当前执行步骤
    base_plan_version: int | None = None  # 基础计划版本
    result_plan_version: int | None = None  # 结果计划版本
    feedback_id: UUID | None = None  # 关联反馈 ID
    repair_attempts: int = Field(ge=0)  # 已修复次数
    max_repair_attempts: int = Field(ge=0)  # 最大修复次数
    error: dict[str, object] | None = None  # 错误信息
    created_at: datetime  # 创建时间
    started_at: datetime | None = None  # 开始时间
    finished_at: datetime | None = None  # 结束时间


class PlanVersionRecord(ApplicationModel):
    id: UUID  # 计划唯一 ID
    trip_id: UUID  # 所属旅行 ID
    version: int = Field(ge=1)  # 计划版本号
    parent_version: int | None  # 父版本号
    status: PlanStatus  # 计划状态
    itinerary: Itinerary  # 行程内容
    constraint_report: ConstraintReport  # 约束检查报告
    change_summary: str  # 变更摘要
    trigger: PlanTrigger  # 触发类型
    planning_run_id: UUID  # 关联规划任务 ID
    created_at: datetime  # 创建时间
    accepted_at: datetime | None = None  # 接受时间


class PlanningEventRecord(ApplicationModel):
    id: str  # 事件唯一 ID
    run_id: UUID  # 所属规划任务 ID
    sequence: int = Field(ge=1)  # 事件序号
    type: PlanningEventType  # 事件类型
    step: str | None  # 事件所属步骤
    message: str  # 事件消息
    payload: dict[str, object] = Field(default_factory=dict)  # 事件附加数据
    created_at: datetime  # 创建时间


class FeedbackRecord(ApplicationModel):
    id: UUID  # 反馈唯一 ID
    trip_id: UUID  # 所属旅行 ID
    base_plan_version: int  # 反馈基于的计划版本
    message: str  # 用户反馈内容
    operations: list[dict[str, object]]  # 结构化反馈操作
    affected_dates: list[date] = Field(default_factory=list)  # 受影响的日期
    affected_activity_ids: list[UUID] = Field(default_factory=list)  # 受影响的活动 ID
    global_scope: bool = True  # 是否全局反馈
    requires_clarification: bool  # 是否需要用户澄清
    clarification_question: str | None  # 澄清问题
    planning_run_id: UUID | None  # 关联规划任务 ID
    created_at: datetime


class LLMCallRecord(ApplicationModel):
    """记录每一次大模型调用的审计流水。"""
    id: UUID
    trip_id: UUID
    task: str  # e.g. "parse_feedback", "rerank_places", "generate_summary"
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    created_at: datetime
