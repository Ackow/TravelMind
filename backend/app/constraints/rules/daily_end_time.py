from datetime import time
from zoneinfo import ZoneInfo

from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


class DailyEndTimeRule:
    """检查每个活动是否在用户设置的每日最晚时间前结束。

    活动时间先转换到行程目的地时区再比较，结束时间刚好等于上限时通过。
    """

    code = ConstraintCode.DAILY_END_TIME_EXCEEDED  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """返回所有超过每日最晚结束时间的活动。"""
        violations: list[ConstraintViolation] = []
        limit = time.fromisoformat(context.request.constraints.daily_end_time)
        destination_timezone = ZoneInfo(itinerary.timezone)

        for day in itinerary.days:
            for activity in day.activities:
                # 去掉时区信息后，只比较目的地当地的时、分、秒。
                local_end = (
                    activity.end_at.astimezone(destination_timezone).time().replace(tzinfo=None)
                )
                if local_end <= limit:
                    continue

                violations.append(
                    make_violation(
                        code=self.code,
                        severity=ConstraintSeverity.ERROR,
                        day=day.date,
                        activity_id=activity.id,
                        message=f"活动“{activity.title}”超过每日最晚结束时间",
                        actual={"end_time": local_end.isoformat()},
                        expected={"latest_end_time": limit.isoformat()},
                        repair_hint="缩短活动或将其移动到更早时间",
                        rule_version=self.version,
                    )
                )

        return violations
