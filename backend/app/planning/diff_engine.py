from datetime import UTC, datetime

from app.domain.common import Money
from app.domain.itinerary import Itinerary
from app.domain.replanning import (
    ActivityChange,
    DiffChangeType,
    MetricDelta,
    PlanDiff,
)


def calculate_plan_diff(
    old_plan: Itinerary,
    new_plan: Itinerary,
    from_version: int,
    to_version: int,
) -> PlanDiff:
    """计算两版行程之间的结构化变动明细与宏观统计指标 Delta。"""
    now_dt = datetime.now(UTC)
    
    # 构建老版本与新版本的活动索引表
    old_activities = {
        act.id: (day.date, act)
        for day in old_plan.days
        for act in day.activities
    }
    new_activities = {
        act.id: (day.date, act)
        for day in new_plan.days
        for act in day.activities
    }

    added: list[ActivityChange] = []
    removed: list[ActivityChange] = []
    modified: list[ActivityChange] = []
    unchanged_count = 0
    affected_dates_set = set()

    # 检查新版本中的变动（Added & Modified）
    for act_id, (new_day, new_act) in new_activities.items():
        if act_id not in old_activities:
            added.append(
                ActivityChange(
                    activity_id=act_id,
                    place_name=new_act.title,
                    day=new_day,
                    change_type=DiffChangeType.ADDED,
                    new_start_at=new_act.start_at,
                    new_end_at=new_act.end_at,
                    cost_delta=new_act.estimated_cost,
                    reason=new_act.reason,
                )
            )
            affected_dates_set.add(new_day)
        else:
            old_day, old_act = old_activities[act_id]
            is_time_changed = old_act.start_at != new_act.start_at or old_act.end_at != new_act.end_at
            is_title_changed = old_act.title != new_act.title
            
            if is_time_changed or is_title_changed:
                modified.append(
                    ActivityChange(
                        activity_id=act_id,
                        place_name=new_act.title,
                        day=new_day,
                        change_type=DiffChangeType.MODIFIED,
                        old_start_at=old_act.start_at,
                        new_start_at=new_act.start_at,
                        old_end_at=old_act.end_at,
                        new_end_at=new_act.end_at,
                        reason="时间或地点微调",
                    )
                )
                affected_dates_set.add(new_day)
            else:
                unchanged_count += 1

    # 检查老版本中被删除的活动（Removed）
    for act_id, (old_day, old_act) in old_activities.items():
        if act_id not in new_activities:
            removed.append(
                ActivityChange(
                    activity_id=act_id,
                    place_name=old_act.title,
                    day=old_day,
                    change_type=DiffChangeType.REMOVED,
                    old_start_at=old_act.start_at,
                    old_end_at=old_act.end_at,
                    cost_delta=old_act.estimated_cost,
                    reason="根据重规划需求裁剪",
                )
            )
            affected_dates_set.add(old_day)

    # 统计宏观 Delta
    old_cost = old_plan.budget.planned_total.amount / 100.0 if old_plan.budget else 0.0
    new_cost = new_plan.budget.planned_total.amount / 100.0 if new_plan.budget else 0.0
    currency = old_plan.budget.currency if old_plan.budget else "CNY"

    old_walking = sum(day.statistics.walking_meters for day in old_plan.days)
    new_walking = sum(day.statistics.walking_meters for day in new_plan.days)

    cost_delta = MetricDelta(
        before_value=old_cost,
        after_value=new_cost,
        delta_value=round(new_cost - old_cost, 2),
        unit=currency,
    )
    
    walking_delta = MetricDelta(
        before_value=old_walking,
        after_value=new_walking,
        delta_value=new_walking - old_walking,
        unit="meters",
    )

    act_count_delta = MetricDelta(
        before_value=len(old_activities),
        after_value=len(new_activities),
        delta_value=len(new_activities) - len(old_activities),
        unit="items",
    )

    # 组装自然语言概要
    summary_parts = [
        f"版本演进: v{from_version} -> v{to_version}。",
        f"受波及天数: {len(affected_dates_set)} 天 ({unchanged_count} 项活动保持未变)。",
    ]
    if added:
        summary_parts.append(f"新增 {len(added)} 处活动（如: {', '.join(a.place_name for a in added[:2])}）。")
    if removed:
        summary_parts.append(f"移除 {len(removed)} 处活动（如: {', '.join(a.place_name for a in removed[:2])}）。")
    if modified:
        summary_parts.append(f"微调 {len(modified)} 处活动的时间或排期。")
    if walking_delta.delta_value != 0:
        walk_txt = f"减少 {abs(walking_delta.delta_value):.0f} 米" if walking_delta.delta_value < 0 else f"增加 {walking_delta.delta_value:.0f} 米"
        summary_parts.append(f"全行程步行量 {walk_txt}。")

    return PlanDiff(
        from_version=from_version,
        to_version=to_version,
        created_at=now_dt,
        total_cost_delta=cost_delta,
        walking_meters_delta=walking_delta,
        activity_count_delta=act_count_delta,
        affected_dates=sorted(affected_dates_set),
        added_activities=added,
        removed_activities=removed,
        modified_activities=modified,
        unchanged_activities_count=unchanged_count,
        human_summary=" ".join(summary_parts),
    )