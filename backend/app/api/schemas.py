from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.models import (
    PlanningEventType,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    TripStatus,
)
from app.application.planning import RunStatus
from app.domain.common import DateRange, Money
from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.domain.trip import TripConstraints, TripPreferences, TripRequest


class ApiModel(BaseModel):
    """所有 HTTP DTO 的共同配置。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# 创建旅行请求：与领域模型字段一致，但不允许客户端提交服务端生成字段
class TripCreateRequest(TripRequest):
    """创建旅行请求。

    它和领域 TripRequest 当前字段相同，但拥有独立的 OpenAPI Schema 名称。
    客户端无法提交 id、status、revision 或 current_plan_version。
    """


class TripResponse(ApiModel):
    id: UUID  # 旅行唯一 ID
    status: TripStatus  # 旅行状态
    revision: int = Field(ge=1)  # 版本号（乐观锁用）
    origin: str  # 出发地
    destination: str  # 目的地
    destination_timezone: str  # 目的地时区
    date_range: DateRange  # 日期区间
    travelers: int  # 出行人数
    preferences: TripPreferences  # 旅行偏好
    constraints: TripConstraints  # 硬性约束
    locale: str  # 语言地区
    display_currency: str  # 展示币种
    notes: str | None  # 用户备注
    current_plan_version: int | None  # 当前生效的计划版本号
    active_planning_run_id: UUID | None  # 正在执行的规划任务 ID
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间


class StartPlanningRequest(ApiModel):
    model: Literal["initial", "regenerate"] = "initial"  # 规划模式：首次生成或重新生成
    force_refresh_tools: bool = False  # 是否强制刷新外部工具数据
    max_repair_attempts: int = Field(default=3, ge=1, le=5)  # 最大修复轮数


class PlanningRunResponse(ApiModel):
    id: UUID
    trip_id: UUID
    trigger: PlanningRunTrigger  # 触发来源
    status: RunStatus  # 运行状态
    progress_percent: int = Field(ge=0, le=100)  # 进度百分比
    current_step: str | None  # 当前步骤
    base_plan_version: int | None  # 基础计划版本
    result_plan_version: int | None  # 结果计划版本
    feedback_id: UUID | None  # 关联反馈 ID
    repair_attempts: int  # 已修复次数
    max_repair_attempts: int
    error: dict[str, object] | None  # 错误信息
    created_at: datetime
    started_at: datetime | None  # 开始时间
    finished_at: datetime | None  # 结束时间


class StartPlanningResponse(ApiModel):
    planning_run: PlanningRunResponse  # 规划任务
    events_url: str  # 事件查询地址


class CurrentPlanResponse(ApiModel):
    id: UUID
    trip_id: UUID
    version: int
    parent_version: int | None
    status: PlanStatus
    itinerary: Itinerary
    constraint_report: ConstraintReport
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime
    accepted_at: datetime | None


class PlanVersionResponse(ApiModel):
    id: UUID
    trip_id: UUID
    version: int = Field(ge=1)
    parent_version: int | None
    status: PlanStatus
    itinerary: Itinerary
    constraint_report: ConstraintReport
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime
    accepted_at: datetime | None


class PlanVersionSummary(ApiModel):
    id: UUID
    trip_id: UUID
    version: int
    parent_version: int | None
    status: PlanStatus
    day_count: int
    planned_total: Money
    error_count: int
    warning_count: int
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime


class PlanListResponse(ApiModel):
    items: list[PlanVersionSummary]


class PlanningEventResponse(ApiModel):
    id: str
    run_id: UUID
    sequence: int = Field(ge=1)
    type: PlanningEventType
    step: str | None
    message: str
    payload: dict[str, object]
    created_at: datetime


class PlanningEventListResponse(ApiModel):
    items: list[PlanningEventResponse]


class SetBudgetOperation(ApiModel):
    op: Literal["set_budget"]  # 操作类型：设置预算
    total_budget: Money  # 总预算
    hard_limit: bool  # 是否硬性限制
    reason: str | None = Field(default=None, max_length=500)


class SetMaxWalkingOperation(ApiModel):
    op: Literal["set_max_walking"]  # 操作类型：设置每日步行上限
    meters_per_day: int = Field(ge=1000, le=50000)  # 每日步行上限（米）
    reason: str | None = Field(default=None, max_length=500)


class AddRequiredPlaceOperation(ApiModel):
    op: Literal["add_required_place"]  # 操作类型：新增必去地点
    place_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=500)


class AddExcludedPlaceOperation(ApiModel):
    op: Literal["add_excluded_place"]  # 操作类型：新增排除地点
    place_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=500)


# 反馈操作联合类型：按 op 字段自动判别具体操作
FeedbackOperation = Annotated[
    SetBudgetOperation
    | SetMaxWalkingOperation
    | AddRequiredPlaceOperation
    | AddExcludedPlaceOperation,
    Field(discriminator="op"),
]


class FeedbackCreateRequest(ApiModel):
    base_plan_version: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=2000)  # 用户反馈内容
    client_operations: list[FeedbackOperation] = Field(default_factory=list)  # 结构化反馈操作列表
    auto_start_replanning: bool = True  # 是否自动触发重新规划


class FeedbackScope(ApiModel):
    dates: list[date] = Field(default_factory=list)  # 受影响的日期
    activity_ids: list[UUID] = Field(default_factory=list)  # 受影响的活动 ID
    global_: bool = Field(default=True, alias="global")  # 是否全局范围

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class FeedbackRecordResponse(ApiModel):
    id: UUID
    trip_id: UUID
    base_plan_version: int
    message: str
    operations: list[FeedbackOperation]
    scope: FeedbackScope
    requires_clarification: bool
    clarification_question: str | None
    planning_run_id: UUID | None
    created_at: datetime


class FeedbackResponse(ApiModel):
    feedback: FeedbackRecordResponse
    planning_run: PlanningRunResponse | None
    events_url: str | None


class ManualActivityEdit(ApiModel):
    id: UUID
    title: str = Field(min_length=1, max_length=200)  # 活动标题
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")  # 开始时间 HH:MM
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")  # 结束时间 HH:MM
    removed: bool = False  # 是否删除该活动
    is_new: bool = False  # 是否新增活动


class ManualDayEdit(ApiModel):
    date: date  # 日期
    activities: list[ManualActivityEdit]  # 当天活动编辑列表


# 手动编辑计划请求：按天提交活动的新增/替换/删除/时间调整
class ManualPlanEditRequest(ApiModel):
    base_plan_version: int = Field(ge=1)
    days: list[ManualDayEdit] = Field(min_length=1)  # 按天提交的编辑内容


class ManualPlanEditResponse(ApiModel):
    plan: CurrentPlanResponse
    planning_run: PlanningRunResponse
