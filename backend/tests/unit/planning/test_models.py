from datetime import datetime

import pytest

from app.planning.models import PlannerConfig, PlanningFacts
from app.scripts.generate_fixture_plan import build_fixture_facts


def test_planner_config_rejects_non_positive_meal_duration() -> None:
    """用餐活动时长必须能构造结束晚于开始的合法 Activity。"""
    with pytest.raises(ValueError, match="meal_duration_minutes must be positive"):
        PlannerConfig(meal_duration_minutes=0)


def test_planner_config_rejects_invalid_lunch_hour() -> None:
    """午餐小时必须能够传给 datetime.time。"""
    with pytest.raises(ValueError, match="between 0 and 23"):
        PlannerConfig(lunch_latest_start_hour=24)


def test_planning_facts_reject_naive_planned_at() -> None:
    """规划时间必须带时区，保证生成和检查时间语义明确。"""
    facts = build_fixture_facts()
    with pytest.raises(ValueError, match="planned_at must be timezone-aware"):
        PlanningFacts(
            request=facts.request,
            places=facts.places,
            weather=facts.weather,
            route_matrix=facts.route_matrix,
            exchange_rates=facts.exchange_rates,
            planned_at=datetime(2026, 9, 30),
        )


def test_planning_facts_reject_duplicate_places() -> None:
    """相同 Place ID 重复出现会破坏评分和分区唯一性。"""
    facts = build_fixture_facts()
    with pytest.raises(ValueError, match="place ids must be unique"):
        PlanningFacts(
            request=facts.request,
            places=(*facts.places, facts.places[0]),
            weather=facts.weather,
            route_matrix=facts.route_matrix,
            exchange_rates=facts.exchange_rates,
            planned_at=facts.planned_at,
        )
