from datetime import date, time
from enum import StrEnum

from pydantic import Field, model_validator

from app.domain.common import DomainModel, GeoPoint, Money, SourceRef
from app.domain.trip import TransportMode


class WeatherCondition(StrEnum):
    """天气状况枚举，描述单日天气"""

    CLEAR = "clear"  # 晴朗
    PARTLY_CLOUDY = "partly_cloudy"  # 局部多云
    CLOUDY = "cloudy"  # 阴天
    RAIN = "rain"  # 下雨
    STORM = "storm"  # 暴风雨
    SNOW = "snow"  # 下雪
    FOG = "fog"  # 雾
    UNKNOWN = "unknown"  # 未知


class OutdoorSuitability(StrEnum):
    """户外活动适宜度枚举"""

    GOOD = "good"  # 适宜
    ACCEPTABLE = "acceptable"  # 尚可，可以外出
    POOR = "poor"  # 较差，不建议户外
    UNKNOWN = "unknown"  # 未知


class IndoorOutdoor(StrEnum):
    """场所属性"""

    INDOOR = "indoor"  # 纯室内（博物馆、咖啡馆）
    OUTDOOR = "outdoor"  # 纯室外（公园、观景台）
    MIXED = "mixed"  # 室内外兼有
    UNKNOWN = "unknown"  # 未知


class PlaceCategory(StrEnum):
    """景点/地点分类枚举"""

    ATTRACTION = "attraction"  # 通用景点
    MUSEUM = "museum"  # 博物馆
    PARK = "park"  # 公园
    ANIME = "anime"  # 动漫相关打卡地
    FOOD = "food"  # 美食集合地
    RESTAURANT = "restaurant"  # 餐厅
    CAFE = "cafe"  # 咖啡馆
    SHOPPING = "shopping"  # 购物场所
    NEIGHBORHOOD = "neighborhood"  # 街区/片区
    TEMPLE = "temple"  # 寺庙
    SHRINE = "shrine"  # 神社
    VIEWPOINT = "viewpoint"  # 观景台
    ENTERTAINMENT = "entertainment"  # 娱乐场所


class WeatherDay(DomainModel):
    """某一天目的地的天气预报数据"""

    date: date  # 预报对应日期（仅年月日）
    condition: WeatherCondition  # 天气状况
    temperature_min_c: float | None = None  # 最低气温
    temperature_max_c: float | None = None  # 最高气温
    rain_probability: float | None = Field(default=None, ge=0, le=1)  # 下雨概率
    precipitation_mm: float | None = Field(default=None, ge=0)  # 降雨量毫米
    sunrise_time: time | None = None  # 日出时刻
    sunset_time: time | None = None  # 日落时刻
    outdoor_suitability: OutdoorSuitability  # 户外活动适宜等级
    source: SourceRef  # 数据来源

    @model_validator(mode="after")
    def validate_temperature_range(self) -> "WeatherDay":
        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValueError("temperature_min_c must not exceed temperature_max_c")
        return self


class OpeningPeriod(DomainModel):
    """常规营业时间"""

    day_of_week: int = Field(ge=1, le=7)  # 星期
    open_time: time | None = None  # 开门时刻
    close_time: time | None = None  # 关门时刻
    closed: bool  # True代表本周该日全天休业

    @model_validator(mode="after")
    def validate_times(self) -> "OpeningPeriod":
        """营业时间业务校验
        1. 如果closed=True休业，则不能携带开门、关门时间
        2. 如果营业，则open_time、close_time两者必须同时提供
        3. 第一版不支持跨午夜营业时间（例如22:00‑02:00），关门必须晚于开门
        """
        if self.closed:
            if self.open_time is not None or self.close_time is not None:
                raise ValueError("closed period must not contain opening times")
            return self

        if self.open_time is None or self.close_time is None:
            raise ValueError("open period must contain open_time and close_time")
        if self.close_time <= self.open_time:
            raise ValueError("stage 1 does not support opening periods crossing midnight")
        return self


class SpecialOpeningPeriod(DomainModel):
    """特殊日期营业时间：节假日、临时闭馆、临时调整"""

    date: date  # 发生调整的具体日期
    open_time: time | None  # 特殊开门时间
    close_time: time | None  # 特殊关门时间
    closed: bool  # 该特殊日期是否闭馆
    note: str | None = Field(default=None, max_length=200)  # 备注

    @model_validator(mode="after")
    def validate_times(self) -> "SpecialOpeningPeriod":
        if self.closed:
            if self.open_time is not None or self.close_time is not None:
                raise ValueError("closed special period must not contain times")
            return self
        if self.open_time is None or self.close_time is None:
            raise ValueError("open special period must contain times")
        if self.close_time <= self.open_time:
            raise ValueError("special opening period must end after it starts")
        return self


class Place(DomainModel):
    """描述一个游玩点位全部静态信息"""

    id: str = Field(min_length=1, max_length=100)  # 地点唯一ID
    name: str = Field(min_length=1, max_length=200)  # 名称
    localized_name: str | None = Field(default=None, max_length=200)  # 当地语言名称
    categories: list[PlaceCategory] = Field(min_length=1)  # 分类
    address: str | None = Field(default=None, max_length=500)  # 详细地址
    location: GeoPoint  # 经纬度坐标
    rating: float | None = Field(default=None, ge=0, le=5)  # 评分0‑5分，可为空
    rating_count: int | None = Field(default=None, ge=0)  # 评价总数量
    estimated_visit_minutes: int = Field(ge=15, le=720)  # 预估游玩时长
    indoor_outdoor: IndoorOutdoor  # 室内/室外属性
    opening_periods: list[OpeningPeriod] = Field(default_factory=list)  # 每周常规营业时间
    special_opening_periods: list[SpecialOpeningPeriod] = Field(
        default_factory=list
    )  # 特殊节假日营业时间
    admission: Money | None = None  # 门票费用
    tags: list[str] = Field(default_factory=list)  # 标签，如“适合拍照”
    reservation_required: bool | None = None  # 是否需要预约
    accessible: bool | None = None  # 是否有无障碍设施
    website_url: str | None = None  # 官网地址
    source: SourceRef  # 数据溯源


class RoutePoint(DomainModel):
    """路径点，用于路线矩阵输入"""

    place_id: str
    location: GeoPoint


class RouteMatrixStatus(StrEnum):
    """两点之间路线查询状态枚举"""

    OK = "ok"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class RouteMatrixCell(DomainModel):
    """路线矩阵单格：【A点 → B点，某种交通方式】的通行数据"""

    origin_place_id: str  # 起点id
    destination_place_id: str  # 终点id
    mode: TransportMode  # 交通方式
    status: RouteMatrixStatus  # 路线状态
    duration_minutes: int | None = Field(default=None, ge=0)  # 行程耗时，分钟
    distance_meters: int | None = Field(default=None, ge=0)  # 总路程，米
    walking_meters: int | None = Field(default=None, ge=0)  # 其中步行部分距离，米
    cost: Money | None = None  # 交通花费

    @model_validator(mode="after")
    def validate_metrics(self) -> "RouteMatrixCell":
        """业务校验：状态为OK成功时，耗时、总距离、步行距离必须全部有值，不能为None"""
        metrics = (
            self.duration_minutes,
            self.distance_meters,
            self.walking_meters,
        )
        if self.status == RouteMatrixStatus.OK and any(value is None for value in metrics):
            raise ValueError("ok route cell must contain duration, distance and walking distance")
        return self


class RouteMatrix(DomainModel):
    """完整路线矩阵：批量存放多地点两两之间不同交通方式的通行信息
    行程算法直接读取这个矩阵获取两点之间耗时、距离、花费，不用实时调用地图API
    """

    cells: list[RouteMatrixCell]
    source: SourceRef

    @model_validator(mode="after")
    def validate_unique_pairs(self) -> "RouteMatrix":
        """校验唯一性：同一个【起点‑终点‑交通方式】组合不能重复出现在cells列表"""
        keys = [(cell.origin_place_id, cell.destination_place_id, cell.mode) for cell in self.cells]
        if len(keys) != len(set(keys)):
            raise ValueError("route matrix cells must be unique by origin, destination and mode")
        return self
