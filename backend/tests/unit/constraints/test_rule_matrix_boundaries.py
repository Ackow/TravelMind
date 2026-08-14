from datetime import datetime, timedelta

from app.constraints.context import ConstraintContext
from app.constraints.rules.budget import BudgetRule
from app.constraints.rules.place_selection import ExcludedPlaceRule, RequiredPlaceRule
from app.constraints.rules.walking import WalkingLimitRule
from app.constraints.rules.weather import WeatherCompatibilityRule
from app.domain.constraints import ConstraintCode, ConstraintSeverity
from app.domain.research import Place
from app.fixtures.loader import load_tokyo_weather
from app.scripts.build_fixture_itinerary import build_blank_itinerary
from tests.unit.test_remaining_constraint_rules import (
    activity_data,
    itinerary_with_budget,
    make_context,
    replace_first_day,
    route_data,
)


def test_walking_rule_accepts_exact_limit() -> None:
    """步行距离刚好等于上限时不属于超限。"""
    itinerary = replace_first_day(
        route_legs=[route_data(walking=12000)],
        walking_meters=12000,
    )

    assert WalkingLimitRule().check(itinerary, make_context()) == []


def poor_weather_itinerary(indoor_outdoor: str):
    """构造第一天为恶劣天气的单活动行程。"""
    day = build_blank_itinerary().days[0].date
    start = datetime.fromisoformat(f"{day}T09:00:00+09:00")
    poor_weather = next(
        item for item in load_tokyo_weather() if item.outdoor_suitability == "poor"
    ).model_copy(update={"date": day})
    return replace_first_day(
        activities=[
            activity_data(
                index=0,
                day=day,
                start=start,
                end=start + timedelta(hours=1),
                indoor_outdoor=indoor_outdoor,
            )
        ],
        weather=poor_weather,
    )


def test_weather_rule_warns_for_mixed_activity_in_poor_weather() -> None:
    """恶劣天气中的室内外混合活动只产生 warning。"""
    violations = WeatherCompatibilityRule().check(
        poor_weather_itinerary("mixed"),
        make_context(),
    )

    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.WEATHER_MISMATCH, ConstraintSeverity.WARNING)
    ]


def test_weather_rule_accepts_indoor_activity_in_poor_weather() -> None:
    """恶劣天气不应阻止纯室内游览活动。"""
    assert (
        WeatherCompatibilityRule().check(
            poor_weather_itinerary("indoor"),
            make_context(),
        )
        == []
    )


def test_budget_rule_uses_error_for_hard_limit() -> None:
    """硬预算超过一个最小货币单位时报告 error。"""
    itinerary = itinerary_with_budget(1_000_001, 1_000_001)

    violations = BudgetRule().check(itinerary, make_context())

    assert [(item.code, item.severity) for item in violations] == [
        (ConstraintCode.BUDGET_EXCEEDED, ConstraintSeverity.ERROR)
    ]


def single_sensoji_itinerary():
    """构造只访问浅草寺的有效行程。"""
    day = build_blank_itinerary().days[0].date
    start = datetime.fromisoformat(f"{day}T09:00:00+09:00")
    return replace_first_day(
        activities=[
            activity_data(
                index=0,
                day=day,
                start=start,
                end=start + timedelta(hours=1),
            )
        ]
    )


def test_required_place_rule_reports_unvisited_place() -> None:
    """请求中的必去名称没有对应活动时必须报错。"""
    violations = RequiredPlaceRule().check(
        single_sensoji_itinerary(),
        make_context(required_place_names=["东京国立博物馆"]),
    )

    assert [item.code for item in violations] == [ConstraintCode.REQUIRED_PLACE_MISSING]


def test_excluded_place_rule_accepts_place_that_is_not_visited() -> None:
    """排除地点没有出现在计划中时通过。"""
    assert (
        ExcludedPlaceRule().check(
            single_sensoji_itinerary(),
            make_context(excluded_place_names=["东京国立博物馆"]),
        )
        == []
    )


def test_excluded_place_rule_matches_localized_name() -> None:
    """排除规则必须同时识别 Place.localized_name。"""
    base_context = make_context(excluded_place_names=["Senso-ji"])
    sensoji_data = base_context.places_by_id["tm_place_sensoji"].model_dump(mode="python")
    sensoji_data["localized_name"] = "Senso-ji"
    sensoji = Place.model_validate(sensoji_data)
    places = dict(base_context.places_by_id)
    places[sensoji.id] = sensoji
    context = ConstraintContext(
        request=base_context.request,
        places_by_id=places,
        checked_at=base_context.checked_at,
    )

    violations = ExcludedPlaceRule().check(single_sensoji_itinerary(), context)

    assert [item.code for item in violations] == [ConstraintCode.EXCLUDED_PLACE_PRESENT]
