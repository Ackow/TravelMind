from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.common import DateRange, DomainModel, Money, SourceRef
from app.domain.research import IndoorOutdoor, WeatherDay
from app.domain.trip import TransportMode


class ActivityKind(StrEnum):
    """行程单活动类型枚举"""

    VISIT = "visit"  # 景点游览
    MEAL = "meal"  # 就餐
    REST = "rest"  # 休息
    TRANSFER = "transfer"  # 交通转场
    FREE_TIME = "free_time"  # 自由活动
    CHECK_IN = "check_in"  # 酒店入住
    CHECK_OUT = "check_out"  # 酒店退房


class ActivitySourceType(StrEnum):
    """活动数据来源类型"""

    PLANNER = "planner"  # 规划算法自动生成
    USER = "user"  # 用户手动新增/编辑
    REPLACEMENT = "replacement"  # 替换备选点位生成
    FIXED_RULE = "fixed_rule"  # 固定规则强制生成（如入住退房）


class Activity(DomainModel):
    """行程中单个活动"""

    id: UUID  # 活动唯一标识，重规划时用于追踪同一个活动
    kind: ActivityKind  # 活动类型
    title: str = Field(min_length=1, max_length=200)  # 展示标题
    place_id: str | None = Field(default=None, min_length=1, max_length=100)  # 地点id
    start_at: datetime  # 开始时间
    end_at: datetime  # 结束时间
    route_leg_id: UUID | None = None  # 转场活动关联的路段ID
    estimated_cost: Money  # 活动预估费用
    priority: int = Field(default=50, ge=1, le=100)  # 保留优先级，数值越大越重要
    locked: bool  # 是否锁定，锁定后规划器不会自动修改删除
    indoor_outdoor: IndoorOutdoor  # 室内/室外属性
    reason: str = Field(min_length=1, max_length=500)  # 生成该活动的业务原因
    notes: list[str] = Field(default_factory=list)  # 预约、着装等提示
    source_type: ActivitySourceType = ActivitySourceType.PLANNER  # 活动来源

    @model_validator(mode="after")
    def validate_activity(self) -> "Activity":
        """活动业务完整性校验
        1. 起止时间必须带时区；结束必须晚于开始
        2. TRANSFER转场活动必须关联RouteLeg；非转场不能携带route_leg_id
        3. VISIT游览活动必须绑定地点place_id
        """
        if self.start_at.tzinfo is None:
            raise ValueError("start_at must be timezone-aware")

        if self.end_at.tzinfo is None:
            raise ValueError("end_at must be timezone-aware")

        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")

        if self.kind == ActivityKind.TRANSFER and self.route_leg_id is None:
            raise ValueError("transfer activity must reference a route leg")

        if self.kind != ActivityKind.TRANSFER and self.route_leg_id is not None:
            raise ValueError("only transfer activities may reference route_leg_id")

        if self.kind == ActivityKind.VISIT and self.place_id is None:
            raise ValueError("visit activity must reference a place")

        return self


class DayStatistics(DomainModel):
    """单日行程统计指标"""

    activity_count: int = Field(default=0, ge=0)  # 活动数量
    walking_meters: int = Field(default=0, ge=0)  # 当日总步行米数
    transfer_minutes: int = Field(default=0, ge=0)  # 当日转场耗时总和(分钟)
    planned_minutes: int = Field(default=0, ge=0)  # 游玩活动总时长(分钟)
    estimated_cost: Money  # 当日预估总花费


class RouteLeg(DomainModel):
    """单段行程路段：A点到B点的通行信息"""

    id: UUID  # 路段唯一标识
    origin_place_id: str = Field(min_length=1, max_length=100)  # 起点id
    destination_place_id: str = Field(min_length=1, max_length=100)  # 终点id
    mode: TransportMode  # 交通方式
    departure_time: datetime | None = None  # 出发时间
    arrival_time: datetime | None = None  # 到达时间
    duration_minutes: int = Field(ge=0)  # 间隔时间
    distance_meters: int = Field(ge=0)  # 距离（米）
    walking_meters: int = Field(ge=0)  # 步行距离（米）
    cost: Money | None = None  # 花费
    polyline: str | None = None  # 地图路线polyline编码
    instructions_summary: str | None = Field(default=None, max_length=500)  # 操作说明摘要
    source: SourceRef  # 路线事实来源

    @model_validator(mode="after")
    def validate_route_leg(self) -> "RouteLeg":
        """路段业务校验
        1. 起点终点不能相同
        2. 步行距离不能大于总距离
        3. 出发/到达时间必须成对存在，且均带时区，到达晚于出发
        """
        if self.origin_place_id == self.destination_place_id:
            raise ValueError("route origin and destination must be different")

        if self.walking_meters > self.distance_meters:
            raise ValueError("walking_meters must not exceed distance_meters")

        has_departure = self.departure_time is not None
        has_arrival = self.arrival_time is not None

        if has_departure != has_arrival:
            raise ValueError("departure_time and arrival_time must both be provided")

        if self.departure_time is not None:
            if self.departure_time.tzinfo is None:
                raise ValueError("departure_time must be timezone-aware")

            if self.arrival_time is None:
                raise ValueError("arrival_time is required")

            if self.arrival_time.tzinfo is None:
                raise ValueError("arrival_time must be timezone-aware")

            if self.arrival_time <= self.departure_time:
                raise ValueError("arrival_time must be after departure_time")

        return self


class DayPlan(DomainModel):
    """单日行程：某一天全部活动、路段、天气、统计、警告"""

    date: date  # 当地日期
    day_number: int = Field(ge=1)  # 游玩天数
    theme: str = Field(default="待规划", min_length=1, max_length=100)  # 游玩主题
    weather: WeatherDay | None = None  # 天气
    activities: list[Activity] = Field(default_factory=list)  # 活动列表，按照开始时间升序
    route_legs: list[RouteLeg] = Field(default_factory=list)  # 行程涉及的路段
    statistics: DayStatistics  # 单日统计汇总
    warnings: list[str] = Field(default_factory=list)  # 面向用户的提醒

    @model_validator(mode="after")
    def validate_day_plan(self) -> "DayPlan":
        """单日行程校验
        1. 当天内activity、route_leg ID唯一
        2. 所有活动的起止日期必须和本day date一致（不能跨天活动，MVP约定）
        3. activities列表必须已经按start_at升序排好序
        4. activity引用的route_leg_id必须存在于本day_plan的route_legs列表
        """
        activity_ids = [activity.id for activity in self.activities]

        if len(activity_ids) != len(set(activity_ids)):
            raise ValueError("activity ids must be unique within a day")

        route_leg_ids = [route.id for route in self.route_legs]
        if len(route_leg_ids) != len(set(route_leg_ids)):
            raise ValueError("route leg ids must be unique within a day")

        for activity in self.activities:
            if activity.start_at.date() != self.date:
                raise ValueError("activity start date must match day plan date")

            if activity.end_at.date() != self.date:
                raise ValueError("activity end date must match day plan date")

        sorted_activities = sorted(
            self.activities,
            key=lambda activity: activity.start_at,
        )
        if self.activities != sorted_activities:
            raise ValueError("activities must be ordered by start_at")

        known_route_ids = set(route_leg_ids)
        for activity in self.activities:
            if activity.route_leg_id is not None and activity.route_leg_id not in known_route_ids:
                raise ValueError("activity references an unknown route leg")

        return self


class BudgetCategory(StrEnum):
    """预算分类枚举"""

    INTERCITY_TRANSPORT = "intercity_transport"  # 城际交通
    ACCOMMODATION = "accommodation"  # 住宿
    FOOD = "food"  # 餐饮
    ADMISSION = "admission"  # 门票
    LOCAL_TRANSPORT = "local_transport"  # 当地市内交通
    SHOPPING = "shopping"  # 购物
    CONTINGENCY = "contingency"  # 备用金/应急
    OTHER = "other"  # 其他


class BudgetItem(DomainModel):
    """单条预算明细"""

    id: UUID  # 预算明细唯一标识
    category: BudgetCategory  # 费用分类
    label: str = Field(min_length=1, max_length=200)  # 费用名称
    date: date | None  # 费用发生日期
    activity_id: UUID | None = None  # 关联活动ID
    amount: Money  # 已换算到汇总币种的金额
    estimated: bool  # True=预估；False=用户录入确定金额
    source: SourceRef | None = None  # 价格数据来源


class ExchangeRate(DomainModel):
    """汇率领域模型，用于多币种预算换算"""

    from_currency: str = Field(pattern=r"^[A-Z]{3}$")  # 原始币种
    to_currency: str = Field(pattern=r"^[A-Z]{3}$")  # 目标币种
    rate: float = Field(gt=0)  # 换算汇率
    fetched_at: datetime  # 汇率获取时间
    source: SourceRef | None = None  # 汇率数据来源

    @model_validator(mode="after")
    def validate_fetched_at(self) -> "ExchangeRate":
        """汇率拉取时间必须带时区"""
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        return self


class BudgetSummary(DomainModel):
    """预算汇总"""

    limit: Money  # 用户设置的总预算上限
    items: list[BudgetItem] = Field(default_factory=list)  # 预算明细
    totals_by_category: dict[BudgetCategory, Money] = Field(default_factory=dict)  # 分类汇总
    planned_total: Money  # 所有明细的计划总额
    remaining_amount: int  # 剩余金额，可为负数
    currency: str = Field(pattern=r"^[A-Z]{3}$")  # 汇总展示币种
    within_budget: bool  # 是否在预算范围内
    exchange_rates: dict[str, ExchangeRate] = Field(default_factory=dict)  # 换汇信息

    @model_validator(mode="after")
    def validate_summary(self) -> "BudgetSummary":
        """预算强一致性校验
        1. limit/planned_total/item/category‑total 货币单位必须全部一致
        2. planned_total 必须等于所有budget item金额之和
        3. remaining_amount = limit.amount - planned_total.amount
        4. within_budget布尔值必须和剩余金额>=0保持一致
        5. totals_by_category分类汇总必须和明细分类累加结果严格匹配
        """
        if self.limit.currency != self.currency:
            raise ValueError("limit currency must match summary currency")

        if self.planned_total.currency != self.currency:
            raise ValueError("planned_total currency must match summary currency")

        for item in self.items:
            if item.amount.currency != self.currency:
                raise ValueError("budget items must be converted to summary currency")

        for total in self.totals_by_category.values():
            if total.currency != self.currency:
                raise ValueError("category totals must use summary currency")

        expected_total = sum(item.amount.amount for item in self.items)

        if self.planned_total.amount != expected_total:
            raise ValueError("planned_total must equal the sum of budget items")

        expected_remaining = self.limit.amount - self.planned_total.amount

        if self.remaining_amount != expected_remaining:
            raise ValueError("remaining_amount does not match budget totals")

        if self.within_budget != (expected_remaining >= 0):
            raise ValueError("within_budget does not match remaining_amount")

        expected_category_totals: dict[BudgetCategory, int] = {}

        for item in self.items:
            expected_category_totals[item.category] = (
                expected_category_totals.get(item.category, 0) + item.amount.amount
            )

        actual_category_totals = {
            category: money.amount for category, money in self.totals_by_category.items()
        }

        if actual_category_totals != expected_category_totals:
            raise ValueError("totals_by_category does not match budget items")

        return self


class Itinerary(DomainModel):
    """完整行程"""

    trip_id: UUID  # 所属旅行ID
    title: str = Field(min_length=1, max_length=200)  # 行程标题
    destination: str = Field(min_length=1, max_length=100)  # 目的地城市
    timezone: str  # 目的地IANA时区
    date_range: DateRange  # 旅行日期范围
    days: list[DayPlan] = Field(default_factory=list)  # 按日期升序排列的每日计划
    budget: BudgetSummary  # 整体预算汇总
    general_notes: list[str] = Field(default_factory=list)  # 全局注意事项
    generated_at: datetime  # 行程生成时间

    @model_validator(mode="after")
    def validate_days(self) -> "Itinerary":
        """顶层行程校验
        1. 生成时间必须带时区
        2. days数量必须和date_range总天数完全相等
        3. days列表严格按日期升序，完整覆盖date_range每一天，不能缺天、乱序
        """
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")

        if len(self.days) != self.date_range.day_count:
            raise ValueError("itinerary must contain one day plan per trip date")

        expected_dates = [
            self.date_range.start_date + timedelta(days=offset)
            for offset in range(self.date_range.day_count)
        ]
        actual_dates = [day.date for day in self.days]
        if actual_dates != expected_dates:
            raise ValueError("day plans must be ordered and cover the complete date range")

        return self
