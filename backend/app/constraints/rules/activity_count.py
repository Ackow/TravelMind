from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import ActivityKind, Itinerary

# 只统计用户实际参与的游玩活动，结构性的交通、入住和退房不计入上限。
COUNTED_ACTIVITY_KINDS = {
    ActivityKind.VISIT,
    ActivityKind.MEAL,
    ActivityKind.REST,
    ActivityKind.FREE_TIME,
}


class ActivityCountRule:
    """检查每日游玩活动数量是否超过用户设置的上限。"""

    code = ConstraintCode.TOO_MANY_ACTIVITIES
    version = "1.0.0"

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """数量恰好等于上限时通过，只报告严格超过上限的日期。"""
        violations: list[ConstraintViolation] = []
        limit = context.request.constraints.max_activities_per_day

        for day in itinerary.days:
            actual_count = sum(
                activity.kind in COUNTED_ACTIVITY_KINDS for activity in day.activities
            )
            if actual_count <= limit:
                continue

            violations.append(
                make_violation(
                    code=self.code,
                    severity=ConstraintSeverity.ERROR,
                    day=day.date,
                    message="当天安排的游玩活动数量超过用户上限",
                    actual={"activity_count": actual_count},
                    expected={"maximum_activities": limit},
                    repair_hint="删除低优先级活动或移动到其他日期",
                    rule_version=self.version,
                )
            )

        return violations
