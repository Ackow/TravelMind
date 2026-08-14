from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.domain.itinerary import (
    Activity,
    BudgetSummary,
    DayPlan,
    DayStatistics,
    Itinerary,
)


def make_transfer_activity(route_leg_id: UUID) -> Activity:
    return Activity(
        id=uuid4(),
        kind="transfer",
        title="前往上野",
        place_id=None,
        start_at="2026-10-01T11:30:00+09:00",
        end_at="2026-10-01T12:00:00+09:00",
        route_leg_id=route_leg_id,
        estimated_cost={"amount": 180, "currency": "JPY"},
        priority=50,
        locked=False,
        indoor_outdoor="unknown",
        reason="连接两个活动",
        notes=[],
        source_type="planner",
    )


def make_empty_statistics() -> DayStatistics:
    return DayStatistics(
        activity_count=0,
        walking_meters=0,
        transfer_minutes=0,
        planned_minutes=0,
        estimated_cost={"amount": 0, "currency": "JPY"},
    )


def test_budget_summary_rejects_incorrect_remaining_amount() -> None:
    with pytest.raises(ValidationError, match="remaining_amount does not match"):
        BudgetSummary(
            limit={"amount": 10000, "currency": "CNY"},
            planned_total={"amount": 0, "currency": "CNY"},
            remaining_amount=9000,
            currency="CNY",
            within_budget=True,
        )


def test_itinerary_rejects_missing_day() -> None:
    with pytest.raises(ValidationError, match="one day plan per trip date"):
        Itinerary.model_validate(
            {
                "trip_id": str(UUID("00000000-0000-0000-0000-000000000001")),
                "title": "东京 5 日游",
                "destination": "东京",
                "timezone": "Asia/Tokyo",
                "date_range": {
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-05",
                },
                "days": [],
                "budget": {
                    "limit": {"amount": 1000000, "currency": "CNY"},
                    "planned_total": {"amount": 0, "currency": "CNY"},
                    "remaining_amount": 1000000,
                    "currency": "CNY",
                    "within_budget": True,
                },
                "general_notes": [],
                "generated_at": datetime.now(UTC).isoformat(),
            }
        )


def test_activity_accepts_valid_visit() -> None:
    activity = Activity(
        id=uuid4(),
        kind="visit",
        title="浅草寺",
        place_id="tm_place_sensoji",
        start_at="2026-10-01T09:00:00+09:00",
        end_at="2026-10-01T10:30:00+09:00",
        route_leg_id=None,
        estimated_cost={"amount": 0, "currency": "JPY"},
        priority=80,
        locked=False,
        indoor_outdoor="outdoor",
        reason="符合城市漫步偏好",
        notes=[],
        source_type="planner",
    )

    assert activity.estimated_cost.amount == 0
    assert activity.place_id == "tm_place_sensoji"


def test_activity_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError, match="end_at must be after start_at"):
        Activity(
            id=uuid4(),
            kind="visit",
            title="浅草寺",
            place_id="tm_place_sensoji",
            start_at="2026-10-01T10:00:00+09:00",
            end_at="2026-10-01T09:00:00+09:00",
            route_leg_id=None,
            estimated_cost={"amount": 0, "currency": "JPY"},
            priority=80,
            locked=False,
            indoor_outdoor="outdoor",
            reason="符合城市漫步偏好",
            notes=[],
            source_type="planner",
        )


def test_transfer_activity_requires_route_leg() -> None:
    with pytest.raises(
        ValidationError,
        match="transfer activity must reference a route leg",
    ):
        Activity(
            id=uuid4(),
            kind="transfer",
            title="前往上野",
            place_id=None,
            start_at="2026-10-01T11:30:00+09:00",
            end_at="2026-10-01T12:00:00+09:00",
            route_leg_id=None,
            estimated_cost={"amount": 180, "currency": "JPY"},
            priority=50,
            locked=False,
            indoor_outdoor="unknown",
            reason="连接两个活动",
            notes=[],
            source_type="planner",
        )


def test_day_plan_rejects_unknown_route_reference() -> None:
    activity = make_transfer_activity(route_leg_id=uuid4())

    with pytest.raises(ValidationError, match="unknown route leg"):
        DayPlan(
            date="2026-10-01",
            day_number=1,
            theme="浅草与上野",
            weather=None,
            activities=[activity],
            route_legs=[],
            statistics=make_empty_statistics(),
            warnings=[],
        )
