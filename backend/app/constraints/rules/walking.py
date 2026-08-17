from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


class WalkingLimitRule:
    """检查每日步行距离上限，并验证统计缓存是否准确。

    实际步行距离始终从当天 RouteLeg 重新求和，不能直接信任可能过期的
    DayStatistics.walking_meters。
    """

    code = ConstraintCode.MAX_WALKING_EXCEEDED  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """返回步行超限错误和统计值不一致警告。"""
        violations: list[ConstraintViolation] = []
        limit = context.request.constraints.max_walking_meters_per_day

        for day in itinerary.days:
            # RouteLeg 是路线事实来源，以它重新计算真实步行总量。
            actual_walking = sum(route_leg.walking_meters for route_leg in day.route_legs)

            if limit is not None and actual_walking > limit:
                violations.append(
                    make_violation(
                        code=self.code,
                        severity=ConstraintSeverity.ERROR,
                        day=day.date,
                        message="当天步行距离超过用户上限",
                        actual={"walking_meters": actual_walking},
                        expected={"maximum_walking_meters": limit},
                        repair_hint="更换交通方式或减少跨区域活动",
                        rule_version=self.version,
                        discriminator="walking-limit",
                    )
                )

            if day.statistics.walking_meters != actual_walking:
                violations.append(
                    make_violation(
                        code=ConstraintCode.DATA_INCOMPLETE,
                        severity=ConstraintSeverity.WARNING,
                        day=day.date,
                        message="单日步行统计与路线事实不一致",
                        actual={
                            "statistics_walking_meters": day.statistics.walking_meters,
                        },
                        expected={"recalculated_walking_meters": actual_walking},
                        repair_hint="根据当天 RouteLeg 重新计算 DayStatistics",
                        rule_version=self.version,
                        discriminator="walking-statistics",
                    )
                )

        return violations
