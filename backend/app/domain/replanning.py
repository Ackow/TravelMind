from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.domain.common import DomainModel, Money


class ImpactLevel(StrEnum):
    """影响范围严重等级枚举"""
    LOCAL_DAY = "local_day"      # 局部单日影响（例如更换某天下午的景点）
    MULTI_DAY = "multi_day"      # 多日跨天影响（例如指定某两天行程对调）
    GLOBAL = "global"            # 全局影响（例如修改总预算、调整所有天数步行上限）


# ==================== 结构化重规划原子操作 (Patch Operations) ====================

class LockActivityOp(DomainModel):
    """操作：锁定指定活动，禁止算法在后续重规划中删除或挪移"""
    op: Literal["lock_activity"] = "lock_activity"
    activity_id: UUID
    reason: str | None = None


class UnlockActivityOp(DomainModel):
    """操作：解锁指定活动"""
    op: Literal["unlock_activity"] = "unlock_activity"
    activity_id: UUID


class RemovePlaceOp(DomainModel):
    """操作：移除指定地点/活动"""
    op: Literal["remove_place"] = "remove_place"
    place_name: str = Field(min_length=1, max_length=200)
    day: date | None = None # None 表示从所有天中剔除


class ReplacePlaceOp(DomainModel):
    """操作：用目标地点替换指定旧地点"""
    op: Literal["replace_place"] = "replace_place"
    original_place_name: str = Field(min_length=1, max_length=200)
    replacement_place_name: str = Field(min_length=1, max_length=200)
    day: date | None = None


class AdjustDayTimeWindowOp(DomainModel):
    """操作：调整特定日期的作息时间（如推迟出发、提前结束）"""
    op: Literal["adjust_day_time_window"] = "adjust_day_time_window"
    day: date
    start_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ModifyPaceOp(DomainModel):
    """操作：修改指定日期或全局的行程节奏"""
    op: Literal["modify_pace"] = "modify_pace"
    day: date | None = None  # None 表示全局修改
    max_walking_meters: int | None = Field(default=None, ge=1000, le=50000)
    max_activities: int | None = Field(default=None, ge=1, le=10)


class AddBudgetOp(DomainModel):
    """操作：追加或缩减总预算"""
    op: Literal["add_budget"] = "add_budget"
    additional_amount: Money


# 联合类型：支持自动识别与分发的重规划操作
ReplanningOperation = Annotated[
    LockActivityOp
    | UnlockActivityOp
    | RemovePlaceOp
    | ReplacePlaceOp
    | AdjustDayTimeWindowOp
    | ModifyPaceOp
    | AddBudgetOp,
    Field(discriminator="op"),
]


# ==================== 差异比对（Plan Diff）领域模型 ====================

class DiffChangeType(StrEnum):
    ADDED = "added"          # 新增活动
    REMOVED = "removed"      # 移除活动
    MODIFIED = "modified"    # 时间或属性调整
    UNCHANGED = "unchanged"  # 完全无变动


class ActivityChange(DomainModel):
    """单项活动的具体变动明细"""
    activity_id: UUID
    place_name: str
    day: date
    change_type: DiffChangeType
    old_start_at: datetime | None = None
    new_start_at: datetime | None = None
    old_end_at: datetime | None = None
    new_end_at: datetime | None = None
    cost_delta: Money | None = None
    reason: str | None = None


class MetricDelta(DomainModel):
    """统计维度的增量变化"""
    before_value: float
    after_value: float
    delta_value: float
    unit: str


class PlanDiff(DomainModel):
    """两份行程版本之间的完整语义差异报告"""
    from_version: int
    to_version: int
    created_at: datetime
    
    # 宏观指标变化
    total_cost_delta: MetricDelta
    walking_meters_delta: MetricDelta
    activity_count_delta: MetricDelta
    
    # 受波及的日期集合
    affected_dates: list[date]
    
    # 具体活动变动列表
    added_activities: list[ActivityChange]
    removed_activities: list[ActivityChange]
    modified_activities: list[ActivityChange]
    unchanged_activities_count: int
    
    # 自然语言变更摘要
    human_summary: str