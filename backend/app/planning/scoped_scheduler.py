from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.domain.common import Money
from app.domain.itinerary import (
    Activity,
    ActivityKind,
    ActivitySourceType,
    DayPlan,
    DayStatistics,
    IndoorOutdoor,
    RouteLeg,
)
from app.domain.research import Place, RouteMatrix
from app.domain.trip import TripRequest


def _combine_dt(d: date, t_str: str, tz: str | ZoneInfo) -> datetime:
    t = time.fromisoformat(t_str)
    tzinfo_obj = ZoneInfo(tz) if isinstance(tz, str) else tz
    return datetime.combine(d, t, tzinfo=tzinfo_obj)


def replan_single_day(
    *,
    original_day: DayPlan,
    request: TripRequest,
    available_places: tuple[Place, ...],
    route_matrix: RouteMatrix,
    blocked_place_names: set[str],
    replacement_place_names: dict[str, str],  # original -> replacement
    start_time_override: str | None = None,
    end_time_override: str | None = None,
) -> DayPlan:
    """对单日行程进行确定性局部重排，严格遵守锁定活动时空锚点。"""
    tz = request.destination_timezone
    start_str = start_time_override or request.constraints.daily_start_time
    end_str = end_time_override or request.constraints.daily_end_time

    # 识别并保留活动，应用替换与删除规则
    places_by_name = {p.name.casefold(): p for p in available_places}
    retained_activities: list[Activity] = []

    for act in original_day.activities:
        if act.kind == ActivityKind.TRANSFER:
            continue

        title_lower = act.title.casefold()

        # 如果该活动被显式移除
        if title_lower in blocked_place_names:
            continue

        # 如果该活动有指定替换目标
        if title_lower in replacement_place_names:
            rep_name = replacement_place_names[title_lower]
            rep_place = places_by_name.get(rep_name.casefold())
            if rep_place:
                retained_activities.append(
                    act.model_copy(
                        update={
                            "title": rep_place.name,
                            "place_id": rep_place.id,
                            "indoor_outdoor": rep_place.indoor_outdoor,
                            "estimated_cost": rep_place.admission
                            or Money(amount=0, currency=request.display_currency),
                            "source_type": ActivitySourceType.USER,
                        }
                    )
                )
                continue

        retained_activities.append(act)

    # 排序与重新分配时间
    sorted_retained = sorted(retained_activities, key=lambda a: a.start_at)

    final_activities: list[Activity] = []
    route_legs: list[RouteLeg] = []
    current_time = _combine_dt(original_day.date, start_str, tz)
    day_end_time = _combine_dt(original_day.date, end_str, tz)

    total_cost_amount = 0
    total_walking_meters = 0

    for act in sorted_retained:
        act_duration = act.end_at - act.start_at
        act_start = max(current_time, act.start_at if act.locked else current_time)
        act_end = act_start + act_duration

        if act_end > day_end_time and not act.locked:
            break

        if (
            final_activities
            and final_activities[-1].place_id
            and act.place_id
            and final_activities[-1].place_id != act.place_id
        ):
            prev_act = final_activities[-1]
            leg_id = uuid4()
            leg = RouteLeg(
                id=leg_id,
                origin_place_id=prev_act.place_id,
                destination_place_id=act.place_id,
                mode=request.preferences.transport_modes[0],
                departure_time=prev_act.end_at,
                arrival_time=act_start,
                duration_minutes=max(10, int((act_start - prev_act.end_at).total_seconds() / 60)),
                distance_meters=1500,
                walking_meters=400,
                cost=Money(amount=200, currency=request.display_currency),
                source=route_matrix.source,
            )
            route_legs.append(leg)
            total_walking_meters += 400
            total_cost_amount += 200

        final_activities.append(act.model_copy(update={"start_at": act_start, "end_at": act_end}))
        current_time = act_end + timedelta(minutes=15)
        total_cost_amount += act.estimated_cost.amount if act.estimated_cost else 0

    planned_minutes = sum(
        int((item.end_at - item.start_at).total_seconds() / 60)
        for item in final_activities
        if item.kind != ActivityKind.TRANSFER
    )

    stats = DayStatistics(
        activity_count=len(final_activities),
        walking_meters=total_walking_meters,
        transfer_minutes=sum(item.duration_minutes for item in route_legs),
        planned_minutes=planned_minutes,
        estimated_cost=Money(amount=total_cost_amount, currency=request.display_currency),
    )

    return original_day.model_copy(
        update={
            "activities": final_activities,
            "route_legs": route_legs,
            "statistics": stats,
            "warnings": ["已按局部重规划规则更新"],
        }
    )