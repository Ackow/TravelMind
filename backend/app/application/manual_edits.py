from datetime import date, datetime, time
from uuid import UUID

from app.application.clock import Clock
from app.application.errors import ApplicationError
from app.application.facts import FactsFactory
from app.application.planning import (
    PlanningRunRecord,
    PlanVersionRecord,
    get_plan,
    save_manual_plan,
)
from app.application.repository import TravelRepository
from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.domain.common import Money
from app.domain.itinerary import ActivityKind, ActivitySourceType, Itinerary


def _local_datetime(day: date, value: str, template: datetime) -> datetime:
    """把 HH:MM 字符串与指定日期组合成带时区的 datetime。"""
    parsed = time.fromisoformat(value)
    return datetime.combine(day, parsed, tzinfo=template.tzinfo)


def apply_manual_edits(
    *,
    trip_id: UUID,
    base_version: int,
    day_edits: list[dict[str, object]],
    repository: TravelRepository,
    clock: Clock,
    facts_factory: FactsFactory,
) -> tuple[PlanVersionRecord, PlanningRunRecord]:
    """应用用户明确编辑的活动标题、顺序、时间和删除状态。"""

    # 校验旅行和基础版本是否存在且版本未冲突
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    if trip.current_plan_version != base_version:
        raise ApplicationError("VERSION_CONFLICT", "计划版本已经变化", 409)
    base_plan = get_plan(repository, trip_id, base_version)
    if base_plan is None:
        raise ApplicationError("PLAN_NOT_FOUND", "计划不存在", 404)

    itinerary_data = base_plan.itinerary.model_dump(mode="python")
    edits_by_date = {item["date"]: item for item in day_edits}
    now = clock.now()
    places = list(facts_factory.build(trip.request, now).places)
    from app.fixtures.loader import load_nanjing_places

    places.extend(load_nanjing_places())

    places_by_name = {}
    for place in places:
        places_by_name[place.name.casefold()] = place
        if place.localized_name:
            places_by_name[place.localized_name.casefold()] = place

    # 按日期逐个应用用户编辑：支持新增、替换、删除和调整时间
    for day in itinerary_data["days"]:
        edit = edits_by_date.get(day["date"])
        if edit is None:
            continue
        existing = {
            activity["id"]: activity
            for activity in day["activities"]
            if activity["kind"] != ActivityKind.TRANSFER
        }
        edited_activities = []
        for activity_edit in edit["activities"]:
            activity_id = activity_edit["id"]
            if activity_edit["removed"]:
                continue
            is_new = bool(activity_edit.get("is_new", False))
            replacement = places_by_name.get(str(activity_edit["title"]).casefold())
            if activity_id not in existing:
                if not is_new:
                    raise ApplicationError("INVALID_ACTIVITY", "活动不属于所选日期", 422)
                if replacement is None:
                    raise ApplicationError("PLACE_NOT_AVAILABLE", "地点不可用", 422)
                template = next(iter(existing.values()), day["activities"][0])
                start_at = _local_datetime(
                    day["date"], activity_edit["start_time"], template["start_at"]
                )
                end_at = _local_datetime(day["date"], activity_edit["end_time"], template["end_at"])
                edited_activities.append(
                    {
                        "id": activity_id,
                        "kind": ActivityKind.VISIT,
                        "title": activity_edit["title"],
                        "place_id": replacement.id,
                        "start_at": start_at,
                        "end_at": end_at,
                        "route_leg_id": None,
                        "estimated_cost": replacement.admission
                        or Money(amount=0, currency=trip.display_currency),
                        "priority": 50,
                        "locked": False,
                        "indoor_outdoor": replacement.indoor_outdoor,
                        "reason": "用户在行程编辑器中手动新增",
                        "notes": [],
                        "source_type": ActivitySourceType.USER,
                    }
                )
                continue
            activity = existing[activity_id]
            original_title = activity["title"]
            if activity_edit["title"] != original_title and replacement is None:
                raise ApplicationError("PLACE_NOT_AVAILABLE", "替换地点不可用", 422)
            start_at = _local_datetime(
                day["date"],
                activity_edit["start_time"],
                activity["start_at"],
            )
            end_at = _local_datetime(day["date"], activity_edit["end_time"], activity["end_at"])
            activity.update(
                {
                    "title": activity_edit["title"],
                    "place_id": (
                        replacement.id if replacement is not None else activity["place_id"]
                    ),
                    "indoor_outdoor": (
                        replacement.indoor_outdoor
                        if replacement is not None
                        else activity["indoor_outdoor"]
                    ),
                    "start_at": start_at,
                    "end_at": end_at,
                    "source_type": (
                        ActivitySourceType.REPLACEMENT
                        if activity_edit["title"] != original_title
                        else ActivitySourceType.USER
                    ),
                    "reason": "用户在行程编辑器中手动调整",
                }
            )
            edited_activities.append(activity)

        transfers = [
            activity for activity in day["activities"] if activity["kind"] == ActivityKind.TRANSFER
        ]
        day["activities"] = sorted(
            [*edited_activities, *transfers],
            key=lambda activity: activity["start_at"],
        )
        day["statistics"]["activity_count"] = len(edited_activities)
        day["statistics"]["planned_minutes"] = sum(
            int((item["end_at"] - item["start_at"]).total_seconds() // 60)
            for item in edited_activities
        )

    itinerary_data["generated_at"] = now
    itinerary = Itinerary.model_validate(itinerary_data)
    # 手动编辑后重新执行约束校验，确保新计划仍然满足硬性约束
    report = create_default_engine().check(
        itinerary=itinerary,
        context=ConstraintContext(
            request=trip.request,
            places_by_id={place.id: place for place in places},
            checked_at=now,
        ),
    )
    return save_manual_plan(
        trip_id=trip.id,
        base_version=base_version,
        itinerary=itinerary,
        constraint_report=report,
        repository=repository,
        clock=clock,
    )
