from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


class ActivityOverlapRule:
    """活动时间重叠校验规则
    检查同一天内相邻两个活动是否发生时间重叠
    判定条件：后一个活动的开始时间 < 前一个活动的结束时间 → 时间重叠
    """

    code = ConstraintCode.ACTIVITY_OVERLAP
    version = "1.0.0"

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        del context
        violations: list[ConstraintViolation] = []

        for day in itinerary.days:
            for previous, current in zip(
                day.activities,
                day.activities[1:],
                strict=False,
            ):
                if current.start_at < previous.end_at:
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=current.id,
                            message=f"活动{current.title}与{previous.title}时间重叠",
                            actual={
                                "previous_end_at": previous.end_at.isoformat(),
                                "current_start_at": current.start_at.isoformat(),
                            },
                            expected={"overlap_minutes": 0},
                            repair_hint="调整其中一个活动的开始或结束时间",
                            rule_version=self.version,
                            discriminator=str(previous.id),
                        )
                    )

        return violations
