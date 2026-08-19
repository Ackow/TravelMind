from datetime import UTC, date, datetime

from app.constraints.context import ConstraintContext
from app.constraints.rules.date_range import DateRangeRule
from app.constraints.rules.opening_hours import OpeningHoursRule
from app.constraints.rules.overlap import ActivityOverlapRule
from app.domain.constraints import ConstraintCode, ConstraintSeverity
from app.domain.research import Place
from app.domain.trip import TripRequest
from app.fixtures.loader import load_nanjing_places, load_nanjing_trip_request
from tests.factories.constraint_cases import (
    itinerary_with_day_activities,
    visit_activity,
)


def nanjing_context() -> ConstraintContext:
    """创建时间固定、地点事实完整的南京规则上下文。"""
    places = load_nanjing_places()
    return ConstraintContext(
        request=load_nanjing_trip_request(),
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


tokyo_context = nanjing_context


def test_date_range_rule_accepts_activity_on_last_day() -> None:
    """活动在旅行最后一天结束属于合法边界。"""
    itinerary = itinerary_with_day_activities(
        day_index=4,
        activities=[
            visit_activity(
                activity_id=1,
                title="南京博物院",
                place_id="tm_place_nanjing_museum",
                start_at="2026-10-05T10:00:00+08:00",
                end_at="2026-10-05T11:00:00+08:00",
                indoor_outdoor="indoor",
            )
        ],
    )

    assert DateRangeRule().check(itinerary, nanjing_context()) == []


def test_date_range_rule_rejects_request_and_itinerary_range_mismatch() -> None:
    """行程自身合法但与用户请求日期不一致时必须报告错误。"""
    request_data = load_nanjing_trip_request().model_dump(mode="python")
    request_data["date_range"] = {
        "start_date": date(2026, 10, 2),
        "end_date": date(2026, 10, 6),
    }
    request = TripRequest.model_validate(request_data)
    context = nanjing_context()
    shifted_context = ConstraintContext(
        request=request,
        places_by_id=context.places_by_id,
        checked_at=context.checked_at,
    )
    itinerary = itinerary_with_day_activities(day_index=0, activities=[])

    violations = DateRangeRule().check(itinerary, shifted_context)

    assert [item.code for item in violations] == [ConstraintCode.DATE_OUT_OF_RANGE]
    assert violations[0].activity_id is None


def test_overlap_rule_accepts_touching_activity_boundaries() -> None:
    """前一活动结束等于后一活动开始时不算重叠。"""
    itinerary = itinerary_with_day_activities(
        day_index=0,
        activities=[
            visit_activity(
                activity_id=1,
                title="夫子庙",
                place_id="tm_place_fuzimiao",
                start_at="2026-10-01T09:00:00+08:00",
                end_at="2026-10-01T10:00:00+08:00",
                indoor_outdoor="outdoor",
            ),
            visit_activity(
                activity_id=2,
                title="老门东",
                place_id="tm_place_laomendong",
                start_at="2026-10-01T10:00:00+08:00",
                end_at="2026-10-01T11:00:00+08:00",
                indoor_outdoor="outdoor",
            ),
        ],
    )

    assert ActivityOverlapRule().check(itinerary, nanjing_context()) == []


def test_overlap_rule_rejects_one_minute_overlap() -> None:
    """即使只重叠一分钟也必须定位到后一个活动。"""
    itinerary = itinerary_with_day_activities(
        day_index=0,
        activities=[
            visit_activity(
                activity_id=1,
                title="夫子庙",
                place_id="tm_place_fuzimiao",
                start_at="2026-10-01T09:00:00+08:00",
                end_at="2026-10-01T10:01:00+08:00",
                indoor_outdoor="outdoor",
            ),
            visit_activity(
                activity_id=2,
                title="老门东",
                place_id="tm_place_laomendong",
                start_at="2026-10-01T10:00:00+08:00",
                end_at="2026-10-01T11:00:00+08:00",
                indoor_outdoor="outdoor",
            ),
        ],
    )

    violations = ActivityOverlapRule().check(itinerary, nanjing_context())

    assert [item.code for item in violations] == [ConstraintCode.ACTIVITY_OVERLAP]
    assert violations[0].activity_id.int == 2


def test_opening_hours_rule_allows_end_at_closing_time() -> None:
    """活动结束时间恰好等于闭馆时间时通过。"""
    itinerary = itinerary_with_day_activities(
        day_index=0,
        activities=[
            visit_activity(
                activity_id=1,
                title="夫子庙",
                place_id="tm_place_fuzimiao",
                start_at="2026-10-01T21:00:00+08:00",
                end_at="2026-10-01T22:00:00+08:00",
                indoor_outdoor="outdoor",
            )
        ],
    )

    assert OpeningHoursRule().check(itinerary, nanjing_context()) == []


def test_opening_hours_rule_rejects_explicitly_closed_day() -> None:
    """南京博物院在周一明确闭馆，不能安排参观。"""
    itinerary = itinerary_with_day_activities(
        day_index=4,
        activities=[
            visit_activity(
                activity_id=1,
                title="南京博物院",
                place_id="tm_place_nanjing_museum",
                start_at="2026-10-05T10:00:00+08:00",
                end_at="2026-10-05T11:00:00+08:00",
                indoor_outdoor="indoor",
            )
        ],
    )

    violations = OpeningHoursRule().check(itinerary, nanjing_context())

    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.PLACE_CLOSED, ConstraintSeverity.ERROR)
    ]


def test_opening_hours_rule_prefers_special_date_over_weekly_hours() -> None:
    """特殊日期闭馆配置必须覆盖夫子庙当天正常营业的周规则。"""
    context = nanjing_context()
    fuzimiao_data = context.places_by_id["tm_place_fuzimiao"].model_dump(mode="python")
    fuzimiao_data["special_opening_periods"] = [
        {
            "date": date(2026, 10, 1),
            "open_time": None,
            "close_time": None,
            "closed": True,
            "note": "临时闭馆",
        }
    ]
    special_fuzimiao = Place.model_validate(fuzimiao_data)
    places = dict(context.places_by_id)
    places[special_fuzimiao.id] = special_fuzimiao
    special_context = ConstraintContext(
        request=context.request,
        places_by_id=places,
        checked_at=context.checked_at,
    )
    itinerary = itinerary_with_day_activities(
        day_index=0,
        activities=[
            visit_activity(
                activity_id=1,
                title="夫子庙",
                place_id="tm_place_fuzimiao",
                start_at="2026-10-01T09:00:00+08:00",
                end_at="2026-10-01T10:00:00+08:00",
                indoor_outdoor="outdoor",
            )
        ],
    )

    violations = OpeningHoursRule().check(itinerary, special_context)

    assert [item.code for item in violations] == [ConstraintCode.PLACE_CLOSED]
