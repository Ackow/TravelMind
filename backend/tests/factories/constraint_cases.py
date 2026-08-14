from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.constraints.context import ConstraintContext
from app.domain.itinerary import Itinerary
from app.fixtures.loader import load_tokyo_places, load_tokyo_trip_request
from app.scripts.build_fixture_itinerary import build_blank_itinerary


def blank_itinerary_data() -> dict[str, Any]:
    """返回可安全修改的空白行程字典，避免测试之间共享可变数据。"""
    return deepcopy(build_blank_itinerary().model_dump(mode="json"))


def visit_activity(
    *,
    activity_id: int,
    title: str,
    place_id: str,
    start_at: str,
    end_at: str,
    indoor_outdoor: str,
) -> dict[str, Any]:
    """构造满足领域模型要求的游览活动测试数据。"""
    return {
        "id": str(UUID(int=activity_id)),
        "kind": "visit",
        "title": title,
        "place_id": place_id,
        "start_at": start_at,
        "end_at": end_at,
        "route_leg_id": None,
        "estimated_cost": {"amount": 0, "currency": "CNY"},
        "priority": 50,
        "locked": False,
        "indoor_outdoor": indoor_outdoor,
        "reason": "阶段 2 规则测试",
        "notes": [],
        "source_type": "planner",
    }


def itinerary_with_day_activities(
    day_index: int,
    activities: list[dict[str, Any]],
) -> Itinerary:
    """替换指定日期的活动，并通过 model_validate 重新执行领域校验。"""
    data = blank_itinerary_data()
    data["days"][day_index]["activities"] = activities
    data["days"][day_index]["statistics"]["activity_count"] = len(activities)
    return Itinerary.model_validate(data)


def tokyo_context() -> ConstraintContext:
    """创建检查时间固定、地点事实完整的东京规则上下文。"""
    places = load_tokyo_places()
    return ConstraintContext(
        request=load_tokyo_trip_request(),
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
