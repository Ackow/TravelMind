from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.constraints.context import ConstraintContext
from app.constraints.rules import (
    ActivityCountRule,
    BudgetRule,
    DailyEndTimeRule,
    ExcludedPlaceRule,
    RequiredPlaceRule,
    TransferRule,
    WalkingLimitRule,
    WeatherCompatibilityRule,
)
from app.domain.constraints import ConstraintCode, ConstraintSeverity
from app.domain.itinerary import Itinerary
from app.fixtures.loader import (
    load_nanjing_places,
    load_nanjing_route_matrix,
    load_nanjing_trip_request,
    load_nanjing_weather,
)
from app.scripts.build_fixture_itinerary import build_blank_itinerary

ACTIVITY_IDS = [UUID(f"10000000-0000-0000-0000-{index:012d}") for index in range(1, 8)]
ROUTE_ID = UUID("20000000-0000-0000-0000-000000000001")
BUDGET_ITEM_ID = UUID("30000000-0000-0000-0000-000000000001")


def make_context(**constraint_updates: object) -> ConstraintContext:
    """使用南京 fixture 创建规则上下文，并按测试需要覆盖约束。"""
    request = load_nanjing_trip_request()
    if constraint_updates:
        constraints = request.constraints.model_copy(update=constraint_updates)
        request = request.model_copy(update={"constraints": constraints})
    places = load_nanjing_places()
    return ConstraintContext(
        request=request,
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


def activity_data(
    *,
    index: int,
    day,
    start: datetime,
    end: datetime,
    kind: str = "visit",
    place_id: str | None = "tm_place_fuzimiao",
    route_leg_id: UUID | None = None,
    indoor_outdoor: str = "outdoor",
) -> dict:
    """构造满足 Activity 领域模型要求的测试数据。"""
    return {
        "id": ACTIVITY_IDS[index],
        "kind": kind,
        "title": f"测试活动 {index + 1}",
        "place_id": place_id,
        "start_at": start,
        "end_at": end,
        "route_leg_id": route_leg_id,
        "estimated_cost": {"amount": 0, "currency": "CNY"},
        "priority": 50,
        "locked": False,
        "indoor_outdoor": indoor_outdoor,
        "reason": f"{day} 约束规则测试",
        "notes": [],
        "source_type": "fixed_rule",
    }


def replace_first_day(
    *,
    activities: list[dict] | None = None,
    route_legs: list[dict] | None = None,
    walking_meters: int = 0,
    activity_count: int = 0,
    weather: object = ...,
) -> Itinerary:
    """替换空白行程第一天的数据，并重新执行领域模型校验。"""
    data = build_blank_itinerary().model_dump(mode="python")
    first_day = data["days"][0]
    first_day["activities"] = activities or []
    first_day["route_legs"] = route_legs or []
    first_day["statistics"]["walking_meters"] = walking_meters
    first_day["statistics"]["activity_count"] = activity_count
    if weather is not ...:
        first_day["weather"] = weather
    return Itinerary.model_validate(data)


def route_data(*, duration: int = 30, walking: int = 500) -> dict:
    """构造从夫子庙到老门东的路线事实。"""
    return {
        "id": ROUTE_ID,
        "origin_place_id": "tm_place_fuzimiao",
        "destination_place_id": "tm_place_laomendong",
        "mode": "public_transit",
        "departure_time": None,
        "arrival_time": None,
        "duration_minutes": duration,
        "distance_meters": 20000,
        "walking_meters": walking,
        "cost": {"amount": 1500, "currency": "CNY"},
        "polyline": None,
        "instructions_summary": "乘坐公共交通",
        "source": load_nanjing_route_matrix().source,
    }


def test_transfer_rule_checks_route_duration_and_buffer() -> None:
    """交通窗口必须同时容纳路线耗时和十分钟缓冲。"""
    day = build_blank_itinerary().days[0].date
    base = datetime.fromisoformat(f"{day}T09:00:00+08:00")
    activities = [
        activity_data(index=0, day=day, start=base, end=base + timedelta(hours=1)),
        activity_data(
            index=1,
            day=day,
            start=base + timedelta(hours=1),
            end=base + timedelta(hours=2),
            kind="transfer",
            place_id=None,
            route_leg_id=ROUTE_ID,
            indoor_outdoor="mixed",
        ),
        activity_data(
            index=2,
            day=day,
            start=base + timedelta(hours=2),
            end=base + timedelta(hours=3),
            place_id="tm_place_laomendong",
        ),
    ]
    boundary = replace_first_day(
        activities=activities,
        route_legs=[route_data(duration=50)],
        walking_meters=500,
    )
    assert TransferRule().check(boundary, make_context()) == []

    insufficient = replace_first_day(
        activities=activities,
        route_legs=[route_data(duration=51)],
        walking_meters=500,
    )
    violations = TransferRule().check(insufficient, make_context())
    assert {item.code for item in violations} == {ConstraintCode.TRANSFER_TIME_INSUFFICIENT}


def test_daily_end_time_rule_allows_exact_boundary() -> None:
    """活动恰好在 21:00 结束合法，晚一分钟才触发违规。"""
    day = build_blank_itinerary().days[0].date
    base = datetime.fromisoformat(f"{day}T20:00:00+08:00")
    exact = replace_first_day(
        activities=[activity_data(index=0, day=day, start=base, end=base + timedelta(hours=1))]
    )
    assert DailyEndTimeRule().check(exact, make_context()) == []

    late_data = exact.model_dump(mode="python")
    late_data["days"][0]["activities"][0]["end_at"] += timedelta(minutes=1)
    violations = DailyEndTimeRule().check(
        Itinerary.model_validate(late_data),
        make_context(),
    )
    assert [item.code for item in violations] == [ConstraintCode.DAILY_END_TIME_EXCEEDED]


def test_walking_rule_recalculates_route_facts_and_cache() -> None:
    """路线事实决定步行上限，统计缓存不一致时另发警告。"""
    itinerary = replace_first_day(
        route_legs=[route_data(walking=12001)],
        walking_meters=9999,
    )
    violations = WalkingLimitRule().check(itinerary, make_context())
    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.MAX_WALKING_EXCEEDED, ConstraintSeverity.ERROR),
        (ConstraintCode.DATA_INCOMPLETE, ConstraintSeverity.WARNING),
    ]

    unlimited = replace_first_day(
        route_legs=[route_data(walking=15000)],
        walking_meters=15000,
    )
    assert (
        WalkingLimitRule().check(
            unlimited,
            make_context(max_walking_meters_per_day=None),
        )
        == []
    )


def test_weather_rule_handles_poor_and_missing_weather() -> None:
    """恶劣天气阻止室外游览，缺天气则报告数据不完整。"""
    day = build_blank_itinerary().days[0].date
    base = datetime.fromisoformat(f"{day}T09:00:00+08:00")
    visit = activity_data(
        index=0,
        day=day,
        start=base,
        end=base + timedelta(hours=1),
    )
    poor_weather = next(
        item for item in load_nanjing_weather() if item.outdoor_suitability == "poor"
    ).model_copy(update={"date": day})
    poor = replace_first_day(activities=[visit], weather=poor_weather)
    violations = WeatherCompatibilityRule().check(poor, make_context())
    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.WEATHER_MISMATCH, ConstraintSeverity.ERROR)
    ]

    missing = replace_first_day(activities=[visit], weather=None)
    violations = WeatherCompatibilityRule().check(missing, make_context())
    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.DATA_INCOMPLETE, ConstraintSeverity.WARNING)
    ]


def itinerary_with_budget(planned_amount: int, daily_amount: int) -> Itinerary:
    """构造内部自洽的预算汇总，并允许单独设置每日统计。"""
    data = build_blank_itinerary().model_dump(mode="python")
    day = data["days"][0]["date"]
    limit_amount = 500_000
    data["budget"] = {
        "limit": {"amount": limit_amount, "currency": "CNY"},
        "items": [
            {
                "id": BUDGET_ITEM_ID,
                "category": "admission",
                "label": "测试门票",
                "date": day,
                "activity_id": None,
                "amount": {"amount": planned_amount, "currency": "CNY"},
                "estimated": True,
                "source": None,
            }
        ],
        "totals_by_category": {"admission": {"amount": planned_amount, "currency": "CNY"}},
        "planned_total": {"amount": planned_amount, "currency": "CNY"},
        "remaining_amount": limit_amount - planned_amount,
        "currency": "CNY",
        "within_budget": planned_amount <= limit_amount,
        "exchange_rates": {},
    }
    data["days"][0]["statistics"]["estimated_cost"] = {
        "amount": daily_amount,
        "currency": "CNY",
    }
    return Itinerary.model_validate(data)


def test_budget_rule_handles_boundary_soft_limit_and_daily_cache() -> None:
    """刚好花完预算通过，软超限警告，每日统计不一致也警告。"""
    exact = itinerary_with_budget(500_000, 500_000)
    assert BudgetRule().check(exact, make_context()) == []

    over = itinerary_with_budget(500_001, 500_001)
    violations = BudgetRule().check(
        over,
        make_context(budget_is_hard_limit=False),
    )
    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.BUDGET_EXCEEDED, ConstraintSeverity.WARNING)
    ]

    stale = itinerary_with_budget(500_000, 499_999)
    violations = BudgetRule().check(stale, make_context())
    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.DATA_INCOMPLETE, ConstraintSeverity.WARNING)
    ]


def test_place_rules_resolve_names_and_report_unknown_ids() -> None:
    """地点名称通过 Place ID 精确解析，未知 ID 不会静默通过。"""
    day = build_blank_itinerary().days[0].date
    base = datetime.fromisoformat(f"{day}T09:00:00+08:00")
    itinerary = replace_first_day(
        activities=[
            activity_data(
                index=0,
                day=day,
                start=base,
                end=base + timedelta(hours=1),
                place_id="tm_place_fuzimiao",
            )
        ]
    )
    assert (
        RequiredPlaceRule().check(
            itinerary,
            make_context(required_place_names=["  夫子庙  "]),
        )
        == []
    )
    violations = ExcludedPlaceRule().check(
        itinerary,
        make_context(excluded_place_names=["夫子庙"]),
    )
    assert [item.code for item in violations] == [ConstraintCode.EXCLUDED_PLACE_PRESENT]

    unknown_data = itinerary.model_dump(mode="python")
    unknown_data["days"][0]["activities"][0]["place_id"] = "unknown-place"
    violations = RequiredPlaceRule().check(
        Itinerary.model_validate(unknown_data),
        make_context(),
    )
    assert [item.code for item in violations] == [ConstraintCode.DATA_INCOMPLETE]


def test_activity_count_rule_uses_documented_counting_policy() -> None:
    """五个游玩活动加入住仍通过，第六个游玩活动才超限。"""
    day = build_blank_itinerary().days[0].date
    base = datetime.fromisoformat(f"{day}T09:00:00+08:00")
    activities = []
    for index in range(5):
        start = base + timedelta(minutes=index * 30)
        activities.append(
            activity_data(
                index=index,
                day=day,
                start=start,
                end=start + timedelta(minutes=20),
                kind="free_time",
                place_id=None,
                indoor_outdoor="unknown",
            )
        )
    check_in_start = base + timedelta(hours=3)
    activities.append(
        activity_data(
            index=5,
            day=day,
            start=check_in_start,
            end=check_in_start + timedelta(minutes=20),
            kind="check_in",
            place_id=None,
            indoor_outdoor="indoor",
        )
    )
    boundary = replace_first_day(activities=activities, activity_count=6)
    assert ActivityCountRule().check(boundary, make_context()) == []

    extra_start = base + timedelta(hours=4)
    activities.append(
        activity_data(
            index=6,
            day=day,
            start=extra_start,
            end=extra_start + timedelta(minutes=20),
            kind="meal",
            place_id=None,
            indoor_outdoor="indoor",
        )
    )
    over = replace_first_day(activities=activities, activity_count=7)
    violations = ActivityCountRule().check(over, make_context())
    assert [item.code for item in violations] == [ConstraintCode.TOO_MANY_ACTIVITIES]
