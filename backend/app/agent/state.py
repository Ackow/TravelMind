from enum import StrEnum
from typing import Annotated, Any

from typing_extensions import TypedDict

from app.application.models import ConstraintReport
from app.domain.common import GeoPoint
from app.domain.itinerary import Itinerary
from app.domain.research import Place, RouteMatrixCell, WeatherDay
from app.domain.trip import TripRequest


class PlanStatus(StrEnum):
    """Agent 规划状态生命周期。"""

    INIT = "init"  # 初始状态
    RESEARCHING = "researching"  # 正在调用 Provider 获取多源事实
    PLANNING = "planning"  # 正在执行确定性图优化规划
    VALIDATING = "validating"  # 正在进行确定性约束硬规则审核
    REPAIRING = "repairing"  # 正在自反思并执行约束违规修复
    AWAITING_REVIEW = "awaiting_review"  # 挂起中断，等待用户人工审阅
    USER_FEEDBACK = "user_feedback"  # 正在处理用户提出的修改意见
    APPROVED = "approved"  # 用户审阅通过，行程最终确立
    FAILED = "failed"  # 规划失败（超出最大修复尝试或不可恢复错误）


def merge_audit_events(
    left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Reducer: 合并追加审计日志流。"""
    left_list = left or []
    right_list = right or []
    return left_list + right_list


class PlanState(TypedDict, total=False):
    """LangGraph 核心共享状态容器。"""

    # 基础表示与用户意图
    trip_id: str
    request: TripRequest
    destination: str
    center_location: GeoPoint

    # 外部多源事实快照
    places: tuple[Place, ...]
    weather_forecast: tuple[WeatherDay, ...]
    route_matrix_cells: tuple[RouteMatrixCell, ...]
    exchange_rates: dict[str, float]

    # 当前行程方案与约束报告
    current_itinerary: Itinerary | None
    constraint_report: ConstraintReport | None

    # 循环自愈与重试控制
    repair_attempts: int
    max_repair_attempts: int
    applied_repairs: list[str]

    # 人在回路与用户交互
    user_feedback: str | None
    review_summary: str | None

    # 生命周期与事件追踪
    status: PlanStatus
    last_error: str | None
    audit_events: Annotated[list[dict[str, Any]], merge_audit_events]
