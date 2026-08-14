from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from app.domain.common import DateRange, DomainModel, Money


class Pace(StrEnum):
    """行程节奏枚举，控制每日行程松紧程度"""

    RELAXED = "relaxed"  # 宽松
    BALANCED = "balanced"  # 均衡
    PACKED = "packed"  # 紧凑


class TransportMode(StrEnum):
    """可选用的出行交通方式"""

    WALKING = "walking"  # 步行
    PUBLIC_TRANSIT = "public_transit"  # 公共交通（地铁、公交）
    TAXI = "taxi"  # 出租车
    DRIVING = "driving"  # 自驾
    CYCLING = "cycling"  # 骑行
    MIXED = "mixed"  # 多种交通混合


class DietaryPreference(StrEnum):
    """饮食偏好枚举，用于筛选餐厅、餐饮推荐"""

    VEGETARIAN = "vegetarian"  # 素食
    VEGAN = "vegan"  # 纯素
    HALAL = "halal"  # 清真
    KOSHER = "kosher"  # 犹太洁食
    GLUTEN_FREE = "gluten_free"  # 无麸质
    NO_PORK = "no_pork"  # 不吃猪肉
    NO_BEEF = "no_beef"  # 不吃牛肉
    SEAFOOD_FREE = "seafood_free"  # 不吃海鲜
    NUT_FREE = "nut_free"  # 不含坚果


class WeightedPreference(DomainModel):
    """带权重的偏好项
    value：偏好标签
    weight：偏好强度 0<weight≤1，越大代表用户越喜欢
    """

    value: str = Field(min_length=1, max_length=50)
    weight: float = Field(gt=0, le=1)


class TripPreferences(DomainModel):
    """用户行程偏好：主观喜好，不做硬性强制约束，供算法做加权推荐"""

    interests: list[WeightedPreference] = Field(default_factory=list)  # 兴趣点列表，带偏好权重
    avoid: list[str] = Field(default_factory=list)  # 需要避开的标签/地点，软偏好，尽量不安排
    dietary: list[DietaryPreference] = Field(default_factory=list)  # 饮食偏好集合
    transport_modes: list[TransportMode] = Field(  # 允许使用的交通方式；默认：公共交通 + 步行
        default_factory=lambda: [
            TransportMode.PUBLIC_TRANSIT,
            TransportMode.WALKING,
        ]
    )
    accommodation_notes: str | None = Field(
        default=None, max_length=500
    )  # 住宿备注，例如“靠近地铁站”
    pace: Pace = Pace.BALANCED  # 行程节奏
    must_visit_place_names: list[str] = Field(
        default_factory=list
    )  # 希望尽量去到的地点名称（软偏好，非强制）

    @model_validator(mode="after")
    def validate_unique_interests(self) -> "TripPreferences":
        """校验：interests 内部不允许出现重复的兴趣标签"""
        values = [item.value.casefold() for item in self.interests]
        if len(values) != len(set(values)):
            raise ValueError("interest values must be unique")
        return self


class TripConstraints(DomainModel):
    """行程硬性约束条件：算法必须遵守，不满足就不能生成方案"""

    total_budget: Money  # 总预算
    budget_is_hard_limit: bool = True  # 是否严格卡死总预算
    daily_start_time: str = Field(
        default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    )  # 每日行程开始时间
    daily_end_time: str = Field(
        default="21:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    )  # 每日行程结束时间
    max_walking_meters_per_day: int | None = Field(
        default=12000, ge=1000, le=50000
    )  # 每日最大步行距离（米）
    max_activities_per_day: int = Field(default=5, ge=1, le=10)  # 单日最多安排景点/活动数量
    minimum_transfer_buffer_minutes: int = Field(
        default=10, ge=0, le=60
    )  # 景点之间交通换乘预留缓冲时间（分钟）
    rest_minutes_per_day: int = Field(default=60, ge=0, le=240)  # 每日预留休息总时长（分钟）
    required_place_names: list[str] = Field(default_factory=list)  # 必须去的地点，硬性约束
    excluded_place_names: list[str] = Field(default_factory=list)  # 必须排除的地点，硬性约束
    accessible_only: bool = False  # 是否只选择无障碍友好的地点

    @model_validator(mode="after")
    def validate_constraint_consistency(self) -> "TripConstraints":
        """约束一致性校验：
        1. 每日结束时间必须晚于开始时间
        2. 同一个地点不能同时出现在【必须去】和【排除】两个列表
        """
        if self.daily_end_time <= self.daily_start_time:
            raise ValueError("daily_end_time must be after daily_start_time")

        required = {name.casefold() for name in self.required_place_names}
        excluded = {name.casefold() for name in self.excluded_place_names}
        overlap = required & excluded
        if overlap:
            raise ValueError("a place cannot be both required and excluded")
        return self


class TripRequest(DomainModel):
    """用户完整旅行请求领域模型"""

    origin: str = Field(min_length=1, max_length=100)  # 出发城市
    destination: str = Field(min_length=1, max_length=100)  # 目的地城市
    destination_timezone: str  # 目的地IANA时区字符串
    date_range: DateRange  # 出行日期区间
    travelers: int = Field(ge=1, le=6)  # 出行人数
    preferences: TripPreferences  # 偏好设置
    constraints: TripConstraints  # 硬性约束
    locale: str = Field(default="zh-CN", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")  # 语言地区标识
    display_currency: str = Field(default="CNY", pattern=r"^[A-Z]{3}$")  # 界面展示用货币代码
    notes: str | None = Field(default=None, max_length=1000)  # 用户额外备注信息

    @field_validator("destination_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """校验时区字符串是合法IANA时区"""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("destination_timezone must be a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def validate_mvp_scope(self) -> "TripRequest":
        """
        1. 行程天数限制：只能支持3‑7天
        2. 展示货币必须和预算Money对象的货币保持一致
        """
        if not 3 <= self.date_range.day_count <= 7:
            raise ValueError("MVP trips must contain between 3 and 7 days")
        if self.display_currency != self.constraints.total_budget.currency:
            raise ValueError("display currency must match budget currency in stage 1")
        return self
