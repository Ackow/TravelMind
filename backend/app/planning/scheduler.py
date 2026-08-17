from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from app.domain.common import Money
from app.domain.itinerary import (
    Activity,
    ActivityKind,
    ActivitySourceType,
    BudgetCategory,
    BudgetItem,
    DayPlan,
    DayStatistics,
    RouteLeg,
)
from app.domain.research import (
    IndoorOutdoor,
    Place,
    RouteMatrix,
    RouteMatrixCell,
    RouteMatrixStatus,
    WeatherDay,
)
from app.domain.trip import TripRequest
from app.planning.models import CandidateScore, PlannerConfig
from app.planning.money import MoneyConverter

PLANNING_NAMESPACE = UUID("8e5c513c-4d70-4df8-8ab4-38c61c4b3001")


def stable_id(kind: str, *parts: object) -> UUID:
    """根据业务内容生成稳定 ID，禁止在确定性规划中使用 uuid4。"""
    fingerprint = "|".join([kind, *(str(part) for part in parts)])
    return uuid5(PLANNING_NAMESPACE, fingerprint)


# 将日期、时间和时区组合成带时区的 datetime
def local_datetime(target_date: date, value: time, timezone: ZoneInfo) -> datetime:
    return datetime.combine(target_date, value, tzinfo=timezone)


@dataclass(frozen=True, slots=True)
class OpeningWindow:
    """排程器需要的简化营业状态。"""

    known: bool  # 是否已知营业时间
    closed: bool  # 是否闭园
    open_time: time | None  # 开门时间
    close_time: time | None  # 关门时间


@dataclass(frozen=True, slots=True)
class DailySchedule:
    """一天的计划和这一天产生的预算明细。"""

    day: DayPlan  # 当天计划
    budget_items: tuple[BudgetItem, ...]  # 当天预算明细


def opening_window(place: Place, target_date: date) -> OpeningWindow:
    """特殊日期优先于常规周营业时间，与阶段 2 规则保持同一语义。"""
    for period in place.special_opening_periods:
        if period.date == target_date:
            return OpeningWindow(
                known=True,
                closed=period.closed,
                open_time=period.open_time,
                close_time=period.close_time,
            )

    weekday = target_date.isoweekday()
    for period in place.opening_periods:
        if period.day_of_week == weekday:
            return OpeningWindow(
                known=True,
                closed=period.closed,
                open_time=period.open_time,
                close_time=period.close_time,
            )

    # 缺少营业时间不是“全天营业”。排程器允许候选进入，约束规则会产生 warning。
    return OpeningWindow(
        known=False,
        closed=False,
        open_time=None,
        close_time=None,
    )


class DayScheduler:
    """在单日时间窗内贪心安排一个区域的候选地点。"""

    def __init__(
        self,
        *,
        request: TripRequest,
        places: tuple[Place, ...],
        route_matrix: RouteMatrix,
        converter: MoneyConverter,
        config: PlannerConfig,
    ) -> None:
        self._request = request
        self._places_by_id = {place.id: place for place in places}
        self._converter = converter
        self._config = config
        self._timezone = ZoneInfo(request.destination_timezone)
        self._route_index = self._build_route_index(route_matrix)
        self._route_source = route_matrix.source

    def _build_route_index(
        self,
        matrix: RouteMatrix,
    ) -> dict[tuple[str, str], RouteMatrixCell]:
        """每个方向只保留用户允许交通方式中的最佳路线。"""
        mode_order = {
            mode: index for index, mode in enumerate(self._request.preferences.transport_modes)
        }
        grouped: dict[tuple[str, str], list[RouteMatrixCell]] = {}
        for cell in matrix.cells:
            if cell.status != RouteMatrixStatus.OK or cell.mode not in mode_order:
                continue
            grouped.setdefault(
                (cell.origin_place_id, cell.destination_place_id),
                [],
            ).append(cell)

        return {
            key: min(
                cells,
                key=lambda cell: (
                    mode_order[cell.mode],
                    cell.duration_minutes or 0,
                    cell.walking_meters or 0,
                ),
            )
            for key, cells in grouped.items()
        }

    def _route(self, origin_id: str, destination_id: str) -> RouteMatrixCell | None:
        return self._route_index.get((origin_id, destination_id))

    def _order_candidates(
        self,
        candidates: list[CandidateScore],
    ) -> list[CandidateScore]:
        """首个地点按分数选择，后续只在当前地点可达的候选中取最高分。"""
        if not candidates:
            return []
        remaining = sorted(
            candidates,
            key=lambda item: (-item.score, item.place_id),
        )
        ordered = [remaining.pop(0)]
        while remaining:
            previous_id = ordered[-1].place_id
            reachable = [
                item for item in remaining if self._route(previous_id, item.place_id) is not None
            ]
            if not reachable:
                break
            following = min(
                reachable,
                key=lambda item: (-item.score, item.place_id),
            )
            ordered.append(following)
            remaining.remove(following)
        return ordered

    def _fit_visit(
        self,
        *,
        place: Place,
        earliest_start: datetime,
        daily_end: datetime,
    ) -> tuple[datetime, datetime] | None:
        """把活动推迟到开门时间；放不进时间窗就返回 None。"""
        window = opening_window(place, earliest_start.date())
        if window.closed:
            return None

        start_at = earliest_start
        if window.open_time is not None:
            start_at = max(
                start_at,
                local_datetime(earliest_start.date(), window.open_time, self._timezone),
            )
        end_at = start_at + timedelta(minutes=place.estimated_visit_minutes)

        if window.close_time is not None:
            close_at = local_datetime(
                earliest_start.date(),
                window.close_time,
                self._timezone,
            )
            if end_at > close_at:
                return None
        if end_at > daily_end:
            return None
        return start_at, end_at

    def _converted_group_cost(self, money: Money | None) -> Money:
        """把单人费用换算为展示币种，再乘旅行人数。"""
        if money is None:
            return Money(amount=0, currency=self._request.display_currency)
        converted = self._converter.convert(money, self._request.display_currency)
        return Money(
            amount=converted.amount * self._request.travelers,
            currency=converted.currency,
        )

    def _support_activity(
        self,
        *,
        target_date: date,
        index: int,
        kind: ActivityKind,
        title: str,
        place_id: str,
        start_at: datetime,
        duration_minutes: int,
        cost: Money,
    ) -> Activity:
        return Activity(
            id=stable_id("activity", target_date, index, kind.value, place_id),
            kind=kind,
            title=title,
            place_id=place_id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=duration_minutes),
            route_leg_id=None,
            estimated_cost=cost,
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="满足每日用餐或休息需求",
            source_type=ActivitySourceType.PLANNER,
        )

    def schedule(
        self,
        *,
        target_date: date,
        day_number: int,
        weather: WeatherDay | None,
        candidates: list[CandidateScore],
    ) -> DailySchedule:
        """构造一天的活动、路线、预算和统计。"""
        constraints = self._request.constraints
        daily_start = local_datetime(
            target_date,
            time.fromisoformat(constraints.daily_start_time),
            self._timezone,
        )
        daily_end = local_datetime(
            target_date,
            time.fromisoformat(constraints.daily_end_time),
            self._timezone,
        )
        lunch_deadline = local_datetime(
            target_date,
            time(self._config.lunch_latest_start_hour),
            self._timezone,
        )

        activities: list[Activity] = []
        route_legs: list[RouteLeg] = []
        budget_items: list[BudgetItem] = []
        cursor = daily_start
        walking_meters = 0
        meal_added = False
        last_place_id: str | None = None

        # 预留一个用餐活动；有休息要求时再预留一个休息活动名额。
        support_slots = 1 + int(constraints.rest_minutes_per_day > 0)
        visit_limit = max(0, constraints.max_activities_per_day - support_slots)
        ordered = self._order_candidates(candidates)[:visit_limit]

        for candidate in ordered:
            place = self._places_by_id[candidate.place_id]
            route: RouteMatrixCell | None = None
            route_start = cursor
            earliest_visit = cursor

            if last_place_id is not None:
                route = self._route(last_place_id, place.id)
                if route is None:
                    continue
                assert route.duration_minutes is not None
                assert route.walking_meters is not None

                # 如果下一次游览会跨过午餐最晚开始时间，先在当前地点用餐。
                projected_end = cursor + timedelta(
                    minutes=(
                        route.duration_minutes
                        + constraints.minimum_transfer_buffer_minutes
                        + place.estimated_visit_minutes
                    )
                )
                if not meal_added and cursor < lunch_deadline and projected_end > lunch_deadline:
                    meal_cost = Money(
                        amount=(self._config.meal_cost_per_traveler * self._request.travelers),
                        currency=self._request.display_currency,
                    )
                    meal = self._support_activity(
                        target_date=target_date,
                        index=len(activities),
                        kind=ActivityKind.MEAL,
                        title="午餐",
                        place_id=last_place_id,
                        start_at=cursor,
                        duration_minutes=self._config.meal_duration_minutes,
                        cost=meal_cost,
                    )
                    if meal.end_at <= daily_end:
                        activities.append(meal)
                        budget_items.append(
                            BudgetItem(
                                id=stable_id("budget", meal.id),
                                category=BudgetCategory.FOOD,
                                label="午餐",
                                date=target_date,
                                activity_id=meal.id,
                                amount=meal_cost,
                                estimated=True,
                                source=None,
                            )
                        )
                        cursor = meal.end_at
                        meal_added = True

                projected_walking = walking_meters + route.walking_meters
                walking_limit = constraints.max_walking_meters_per_day
                if walking_limit is not None and projected_walking > walking_limit:
                    continue

                route_start = cursor
                route_end = route_start + timedelta(minutes=route.duration_minutes)
                earliest_visit = route_end + timedelta(
                    minutes=constraints.minimum_transfer_buffer_minutes
                )

            visit_window = self._fit_visit(
                place=place,
                earliest_start=earliest_visit,
                daily_end=daily_end,
            )
            if visit_window is None:
                continue
            visit_start, visit_end = visit_window

            if route is not None:
                assert last_place_id is not None
                assert route.duration_minutes is not None
                assert route.distance_meters is not None
                assert route.walking_meters is not None
                route_cost = self._converted_group_cost(route.cost)
                route_leg = RouteLeg(
                    id=stable_id(
                        "route",
                        target_date,
                        last_place_id,
                        place.id,
                        route_start.isoformat(),
                    ),
                    origin_place_id=last_place_id,
                    destination_place_id=place.id,
                    mode=route.mode,
                    departure_time=route_start,
                    arrival_time=(route_start + timedelta(minutes=route.duration_minutes)),
                    duration_minutes=route.duration_minutes,
                    distance_meters=route.distance_meters,
                    walking_meters=route.walking_meters,
                    cost=route_cost,
                    instructions_summary="使用路线矩阵中的确定性路线",
                    source=self._route_source,
                )
                transfer = Activity(
                    id=stable_id("activity", route_leg.id),
                    kind=ActivityKind.TRANSFER,
                    title=f"前往{place.name}",
                    place_id=None,
                    start_at=route_leg.departure_time,
                    end_at=route_leg.arrival_time,
                    route_leg_id=route_leg.id,
                    estimated_cost=route_cost,
                    priority=50,
                    locked=False,
                    indoor_outdoor=IndoorOutdoor.MIXED,
                    reason="连接相邻游览地点",
                    source_type=ActivitySourceType.PLANNER,
                )
                route_legs.append(route_leg)
                activities.append(transfer)
                walking_meters += route.walking_meters
                if route_cost.amount > 0:
                    budget_items.append(
                        BudgetItem(
                            id=stable_id("budget", route_leg.id),
                            category=BudgetCategory.LOCAL_TRANSPORT,
                            label=f"{last_place_id} 至 {place.id} 交通",
                            date=target_date,
                            activity_id=transfer.id,
                            amount=route_cost,
                            estimated=True,
                            source=self._route_source,
                        )
                    )

            admission = self._converted_group_cost(place.admission)
            visit = Activity(
                id=stable_id("activity", target_date, place.id),
                kind=ActivityKind.VISIT,
                title=place.name,
                place_id=place.id,
                start_at=visit_start,
                end_at=visit_end,
                route_leg_id=None,
                estimated_cost=admission,
                priority=max(1, min(100, round(candidate.score))),
                locked=is_required_name(place, self._request),
                indoor_outdoor=place.indoor_outdoor,
                reason="；".join(candidate.reasons[:3]),
                notes=(["该地点需要预约"] if place.reservation_required is True else []),
                source_type=ActivitySourceType.PLANNER,
            )
            activities.append(visit)
            if admission.amount > 0:
                budget_items.append(
                    BudgetItem(
                        id=stable_id("budget", visit.id),
                        category=BudgetCategory.ADMISSION,
                        label=f"{place.name}门票",
                        date=target_date,
                        activity_id=visit.id,
                        amount=admission,
                        estimated=True,
                        source=place.source,
                    )
                )
            cursor = visit.end_at
            last_place_id = place.id

        # 当天有游览但尚未用餐时，在最后一个地点补充用餐活动。
        if last_place_id is not None and not meal_added:
            meal_cost = Money(
                amount=(self._config.meal_cost_per_traveler * self._request.travelers),
                currency=self._request.display_currency,
            )
            meal = self._support_activity(
                target_date=target_date,
                index=len(activities),
                kind=ActivityKind.MEAL,
                title="午餐",
                place_id=last_place_id,
                start_at=cursor,
                duration_minutes=self._config.meal_duration_minutes,
                cost=meal_cost,
            )
            if meal.end_at <= daily_end:
                activities.append(meal)
                budget_items.append(
                    BudgetItem(
                        id=stable_id("budget", meal.id),
                        category=BudgetCategory.FOOD,
                        label="午餐",
                        date=target_date,
                        activity_id=meal.id,
                        amount=meal_cost,
                        estimated=True,
                        source=None,
                    )
                )
                cursor = meal.end_at

        if last_place_id is not None and constraints.rest_minutes_per_day > 0:
            rest = self._support_activity(
                target_date=target_date,
                index=len(activities),
                kind=ActivityKind.REST,
                title="休息",
                place_id=last_place_id,
                start_at=cursor,
                duration_minutes=constraints.rest_minutes_per_day,
                cost=Money(amount=0, currency=self._request.display_currency),
            )
            if rest.end_at <= daily_end:
                activities.append(rest)

        counted_kinds = {
            ActivityKind.VISIT,
            ActivityKind.MEAL,
            ActivityKind.REST,
            ActivityKind.FREE_TIME,
        }
        daily_cost = sum(item.amount.amount for item in budget_items)
        planned_minutes = sum(
            int((item.end_at - item.start_at).total_seconds() / 60)
            for item in activities
            if item.kind != ActivityKind.TRANSFER
        )
        day = DayPlan(
            date=target_date,
            day_number=day_number,
            theme=(
                "、".join(
                    activity.title for activity in activities if activity.kind == ActivityKind.VISIT
                )
                or "自由调整"
            ),
            weather=weather,
            activities=activities,
            route_legs=route_legs,
            statistics=DayStatistics(
                activity_count=sum(item.kind in counted_kinds for item in activities),
                walking_meters=walking_meters,
                transfer_minutes=sum(item.duration_minutes for item in route_legs),
                planned_minutes=planned_minutes,
                estimated_cost=Money(
                    amount=daily_cost,
                    currency=self._request.display_currency,
                ),
            ),
            warnings=[],
        )
        return DailySchedule(day=day, budget_items=tuple(budget_items))


def is_required_name(place: Place, request: TripRequest) -> bool:
    """判断地点是否属于硬性必去列表。"""
    names = {place.name.strip().casefold()}
    if place.localized_name:
        names.add(place.localized_name.strip().casefold())
    required = {name.strip().casefold() for name in request.constraints.required_place_names}
    return bool(names & required)
