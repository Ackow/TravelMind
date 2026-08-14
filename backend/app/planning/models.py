from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.constraints import ConstraintReport
from app.domain.itinerary import ExchangeRate, Itinerary
from app.domain.research import Place, RouteMatrix, WeatherDay
from app.domain.trip import TripRequest


class PlanningStatus(StrEnum):
    """确定性规划的最终状态。"""

    FEASIBLE = "feasible"  # 已生成无 error 的可行计划
    UNSATISFIED = "unsatisfied"  # 在有限修正轮数内无法满足约束


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    """规划算法配置。

    配置集中存放，测试可以覆盖单项参数，算法内部不再散落魔法数字。
    金额字段均使用请求展示币种的最小货币单位。
    """

    max_repair_rounds: int = 3  # 最大修正轮数
    target_zone_size: int = 2  # 每个地理区域期望包含的地点数量
    meal_duration_minutes: int = 60  # 用餐活动时长
    meal_cost_per_traveler: int = 5000  # 每人每餐5000分（50元）
    lunch_latest_start_hour: int = 13  # 如果下一活动会跨过13点，先用餐

    def __post_init__(self) -> None:
        if self.max_repair_rounds < 0:
            raise ValueError("max_repair_rounds must be non-negative")
        if self.target_zone_size < 1:
            raise ValueError("target_zone_size must be positive")
        if self.meal_duration_minutes <= 0:
            raise ValueError("meal_duration_minutes must be positive")
        if self.meal_cost_per_traveler < 0:
            raise ValueError("meal_cost_per_traveler must be non-negative")
        if not 0 <= self.lunch_latest_start_hour <= 23:
            raise ValueError("lunch_latest_start_hour must be between 0 and 23")


@dataclass(frozen=True, slots=True)
class PlanningFacts:
    """一次规划所需的完整只读事实快照。

    planned_at 由调用方传入，规划器不能读取系统当前时间。这样同一份输入可以
    生成完全相同的 Itinerary.generated_at 和 ConstraintReport.checked_at。
    """

    request: TripRequest
    places: tuple[Place, ...]
    weather: tuple[WeatherDay, ...]
    route_matrix: RouteMatrix
    exchange_rates: Mapping[str, ExchangeRate]
    planned_at: datetime

    def __post_init__(self) -> None:
        if self.planned_at.tzinfo is None:
            raise ValueError("planned_at must be timezone-aware")

        place_ids = [place.id for place in self.places]
        if len(place_ids) != len(set(place_ids)):
            raise ValueError("planning place ids must be unique")

        weather_dates = [item.date for item in self.weather]
        if len(weather_dates) != len(set(weather_dates)):
            raise ValueError("planning weather dates must be unique")


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """某地点在某一天的可解释评分。"""

    place_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Zone:
    """通过坐标和路线事实得到的粗粒度地理区域。"""

    id: str
    place_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    """规划器的结构化返回值。

    无解时仍返回最后一次候选行程和约束报告，调用方可以展示确切冲突，
    而不是只收到一个模糊异常。
    """

    status: PlanningStatus
    itinerary: Itinerary
    report: ConstraintReport
    attempts: int
    repair_notes: tuple[str, ...]
