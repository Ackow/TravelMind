from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.domain.constraints import ConstraintCode, ConstraintReport
from app.domain.itinerary import Itinerary
from app.fixtures.loader import (
    load_tokyo_places,
    load_tokyo_route_matrix,
    load_tokyo_trip_request,
)
from app.scripts.build_fixture_itinerary import build_blank_itinerary


def tokyo_context() -> ConstraintContext:
    """构造东京集成场景使用的固定上下文。"""
    places = load_tokyo_places()
    return ConstraintContext(
        request=load_tokyo_trip_request(),
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


def activity(
    *,
    activity_id: int,
    kind: str,
    title: str,
    place_id: str | None,
    start_at: datetime,
    end_at: datetime,
    indoor_outdoor: str,
) -> dict:
    """构造集成冲突场景使用的活动。"""
    return {
        "id": str(UUID(int=activity_id)),
        "kind": kind,
        "title": title,
        "place_id": place_id,
        "start_at": start_at,
        "end_at": end_at,
        "route_leg_id": None,
        "estimated_cost": {"amount": 0, "currency": "CNY"},
        "priority": 50,
        "locked": False,
        "indoor_outdoor": indoor_outdoor,
        "reason": "阶段 2 东京冲突集成测试",
        "notes": [],
        "source_type": "fixed_rule",
    }


def build_conflicting_tokyo_itinerary() -> Itinerary:
    """构造明确触发天气、闭馆、重叠、步行、晚归和预算冲突的行程。"""
    data = build_blank_itinerary().model_dump(mode="python")

    # 第一天：两个自由活动重叠 15 分钟，并且均晚于每日 21:00 上限。
    first_day = data["days"][0]
    first_base = datetime.fromisoformat("2026-10-01T20:30:00+08:00")
    first_day["activities"] = [
        activity(
            activity_id=1,
            kind="free_time",
            title="夜间自由活动一",
            place_id=None,
            start_at=first_base,
            end_at=first_base + timedelta(hours=1),
            indoor_outdoor="unknown",
        ),
        activity(
            activity_id=2,
            kind="free_time",
            title="夜间自由活动二",
            place_id=None,
            start_at=first_base + timedelta(minutes=45),
            end_at=first_base + timedelta(hours=1, minutes=30),
            indoor_outdoor="unknown",
        ),
    ]
    first_day["route_legs"] = [
        {
            "id": str(UUID(int=101)),
            "origin_place_id": "tm_place_fuzimiao",
            "destination_place_id": "tm_place_laomendong",
            "mode": "walking",
            "departure_time": None,
            "arrival_time": None,
            "duration_minutes": 180,
            "distance_meters": 12001,
            "walking_meters": 12001,
            "cost": None,
            "polyline": None,
            "instructions_summary": "步行",
            "source": load_tokyo_route_matrix().source,
        }
    ]
    first_day["statistics"]["activity_count"] = 2
    first_day["statistics"]["walking_meters"] = 12001
    first_day["statistics"]["estimated_cost"] = {
        "amount": 1_000_001,
        "currency": "CNY",
    }

    # 第二天 fixture 为 poor，安排夫子庙室外游览触发天气冲突。
    second_day = data["days"][1]
    second_day["activities"] = [
        activity(
            activity_id=3,
            kind="visit",
            title="夫子庙",
            place_id="tm_place_fuzimiao",
            start_at=datetime.fromisoformat("2026-10-02T09:00:00+08:00"),
            end_at=datetime.fromisoformat("2026-10-02T10:00:00+08:00"),
            indoor_outdoor="outdoor",
        )
    ]
    second_day["statistics"]["activity_count"] = 1

    # 第五天是周一，南京博物院明确闭馆。
    fifth_day = data["days"][4]
    fifth_day["activities"] = [
        activity(
            activity_id=4,
            kind="visit",
            title="南京博物院",
            place_id="tm_place_nanjing_museum",
            start_at=datetime.fromisoformat("2026-10-05T10:00:00+08:00"),
            end_at=datetime.fromisoformat("2026-10-05T11:00:00+08:00"),
            indoor_outdoor="indoor",
        )
    ]
    fifth_day["statistics"]["activity_count"] = 1

    # 总预算超出请求上限一个最小货币单位。
    data["budget"] = {
        "limit": {"amount": 1_000_000, "currency": "CNY"},
        "items": [
            {
                "id": str(UUID(int=201)),
                "category": "other",
                "label": "冲突场景总费用",
                "date": first_day["date"],
                "activity_id": None,
                "amount": {"amount": 1_000_001, "currency": "CNY"},
                "estimated": True,
                "source": None,
            }
        ],
        "totals_by_category": {"other": {"amount": 1_000_001, "currency": "CNY"}},
        "planned_total": {"amount": 1_000_001, "currency": "CNY"},
        "remaining_amount": -1,
        "currency": "CNY",
        "within_budget": False,
        "exchange_rates": {},
    }
    return Itinerary.model_validate(data)


def test_tokyo_blank_case_has_no_error_and_round_trips_json() -> None:
    """合法空白骨架可以运行全部规则并完成报告 JSON 回读。"""
    report = create_default_engine().check(build_blank_itinerary(), tokyo_context())

    assert report.passed is True
    assert report.violations == []
    assert ConstraintReport.model_validate_json(report.model_dump_json()) == report


def test_tokyo_conflict_case_reports_expected_rule_codes() -> None:
    """东京冲突场景必须覆盖教程要求的六类关键错误。"""
    report = create_default_engine().check(
        build_conflicting_tokyo_itinerary(),
        tokyo_context(),
    )
    codes = {item.code for item in report.violations}

    assert report.passed is False
    assert {
        ConstraintCode.WEATHER_MISMATCH,
        ConstraintCode.PLACE_CLOSED,
        ConstraintCode.ACTIVITY_OVERLAP,
        ConstraintCode.MAX_WALKING_EXCEEDED,
        ConstraintCode.DAILY_END_TIME_EXCEEDED,
        ConstraintCode.BUDGET_EXCEEDED,
    } <= codes
