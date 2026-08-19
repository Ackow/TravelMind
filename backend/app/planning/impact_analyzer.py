from dataclasses import dataclass
from datetime import date

from app.domain.itinerary import Itinerary
from app.domain.replanning import (
    AddBudgetOp,
    AdjustDayTimeWindowOp,
    ImpactLevel,
    LockActivityOp,
    ModifyPaceOp,
    RemovePlaceOp,
    ReplacePlaceOp,
    ReplanningOperation,
    UnlockActivityOp,
)


@dataclass(slots=True, frozen=True)
class ImpactScope:
    """影响范围分析结果"""

    level: ImpactLevel
    affected_dates: tuple[date, ...]
    is_global: bool
    explanation: str


def analyze_feedback_impact(
    operations: list[ReplanningOperation],
    current_itinerary: Itinerary,
) -> ImpactScope:
    """分析操作列表，推断受影响的最小日期区间与范围等级。"""
    if not operations:
        return ImpactScope(
            level=ImpactLevel.LOCAL_DAY,
            affected_dates=(),
            is_global=False,
            explanation="无任何结构化操作，行程保持不变。",
        )

    all_itinerary_dates = {day.date for day in current_itinerary.days}
    affected_dates_set: set[date] = set()
    is_global = False
    reasons: list[str] = []

    # 建立【地点名称 -> 所在日期集合】的反向索引
    place_to_dates: dict[str, set[date]] = {}
    activity_to_date: dict[str, date] = {}
    for day in current_itinerary.days:
        for activity in day.activities:
            place_to_dates.setdefault(activity.title.casefold(), set()).add(day.date)
            activity_to_date[str(activity.id)] = day.date

    for op in operations:
        if isinstance(op, AddBudgetOp):
            is_global = True
            reasons.append("总预算发生变更，波及全局预算分配")

        elif isinstance(op, ModifyPaceOp):
            if op.day is None:
                is_global = True
                reasons.append("全局出行节奏/步行上限调整")
            elif op.day in all_itinerary_dates:
                affected_dates_set.add(op.day)
                reasons.append(f"第 {op.day} 天出行节奏单独调整")

        elif isinstance(op, AdjustDayTimeWindowOp):
            if op.day in all_itinerary_dates:
                affected_dates_set.add(op.day)
                reasons.append(f"第 {op.day} 天出发/结束时间窗口调整")

        elif isinstance(op, (LockActivityOp, UnlockActivityOp)):
            act_id_str = str(op.activity_id)
            if act_id_str in activity_to_date:
                affected_dates_set.add(activity_to_date[act_id_str])
                reasons.append(f"活动 [{act_id_str[:8]}] 锁定状态变更")

        elif isinstance(op, RemovePlaceOp):
            if op.day is not None:
                affected_dates_set.add(op.day)
                reasons.append(f"第 {op.day} 天移除地点 [{op.place_name}]")
            else:
                matched_dates = place_to_dates.get(op.place_name.casefold(), set())
                if matched_dates:
                    affected_dates_set.update(matched_dates)
                    reasons.append(f"移除地点 [{op.place_name}] (波及 {len(matched_dates)} 天)")
                else:
                    reasons.append(f"地点 [{op.place_name}] 未在当前行程中出现")

        elif isinstance(op, ReplacePlaceOp):
            if op.day is not None:
                affected_dates_set.add(op.day)
                reasons.append(
                    f"第 {op.day} 天用 [{op.replacement_place_name}] 替换 [{op.original_place_name}]"
                )
            else:
                matched_dates = place_to_dates.get(op.original_place_name.casefold(), set())
                if matched_dates:
                    affected_dates_set.update(matched_dates)
                    reasons.append(
                        f"替换地点 [{op.original_place_name}] (波及 {len(matched_dates)} 天)"
                    )

    if is_global or len(affected_dates_set) == len(all_itinerary_dates):
        return ImpactScope(
            level=ImpactLevel.GLOBAL,
            affected_dates=tuple(sorted(all_itinerary_dates)),
            is_global=True,
            explanation="; ".join(reasons) or "全局重新规划",
        )

    return ImpactScope(
        level=ImpactLevel.LOCAL_DAY if len(affected_dates_set) <= 1 else ImpactLevel.MULTI_DAY,
        affected_dates=tuple(sorted(affected_dates_set)),
        is_global=False,
        explanation="; ".join(reasons) or f"局部重排 {len(affected_dates_set)} 天行程",
    )
