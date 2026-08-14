from dataclasses import dataclass

from app.domain.constraints import ConstraintCode, ConstraintReport
from app.domain.itinerary import Activity, ActivityKind, Itinerary
from app.domain.research import Place
from app.domain.trip import TripRequest


@dataclass(frozen=True, slots=True)
class RepairDecision:
    """本轮修正只阻止一个地点，下轮从事实重新构建行程。"""

    blocked_place_id: str
    reason: str


UNREPAIRABLE_CODES = {
    ConstraintCode.DATE_OUT_OF_RANGE,
    ConstraintCode.DATA_INCOMPLETE,
    ConstraintCode.REQUIRED_PLACE_MISSING,
}


def required_place_ids(
    request: TripRequest,
    places_by_id: dict[str, Place],
) -> set[str]:
    required_names = {name.strip().casefold() for name in request.constraints.required_place_names}
    result = set()
    for place in places_by_id.values():
        names = {place.name.strip().casefold()}
        if place.localized_name:
            names.add(place.localized_name.strip().casefold())
        if names & required_names:
            result.add(place.id)
    return result


def removable_visits(
    *,
    itinerary: Itinerary,
    request: TripRequest,
    places_by_id: dict[str, Place],
    target_day,
) -> list[Activity]:
    """返回未锁定、非必去的游览活动，低优先级和高费用排在前面。"""
    required_ids = required_place_ids(request, places_by_id)
    visits = [
        activity
        for day in itinerary.days
        if target_day is None or day.date == target_day
        for activity in day.activities
        if activity.kind == ActivityKind.VISIT
        and activity.place_id is not None
        and activity.place_id not in required_ids
        and not activity.locked
    ]
    return sorted(
        visits,
        key=lambda item: (
            item.priority,
            -item.estimated_cost.amount,
            str(item.id),
        ),
    )


def choose_repair(
    *,
    report: ConstraintReport,
    itinerary: Itinerary,
    request: TripRequest,
    places_by_id: dict[str, Place],
) -> RepairDecision | None:
    """根据第一个不可通过错误选择一个确定性修正动作。

    删除候选后重新评分和排程，相当于让下一个候选替换它；营业时间和每日
    结束时间也会在重建时自动提前到最早合法时间。
    """
    errors = [item for item in report.violations if item.severity == "error"]
    if not errors:
        return None

    first = errors[0]
    if first.code in UNREPAIRABLE_CODES:
        return None

    target_day = None if first.code == ConstraintCode.BUDGET_EXCEEDED else first.day
    candidates = removable_visits(
        itinerary=itinerary,
        request=request,
        places_by_id=places_by_id,
        target_day=target_day,
    )
    if not candidates:
        return None

    selected = candidates[0]
    assert selected.place_id is not None
    return RepairDecision(
        blocked_place_id=selected.place_id,
        reason=(f"因 {first.code.value} 暂停安排“{selected.title}”，下一轮使用剩余候选重新规划"),
    )
