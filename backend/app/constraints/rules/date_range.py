from zoneinfo import ZoneInfo

from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


class DateRangeRule:
    """日期范围校验规则

    校验行程与活动是否落在用户请求的旅行日期区间内
    两类违规：
    1. 整个行程的总日期范围和用户请求不一致
    2. 单个活动经过时区转换后，时间超出旅行起止日期
    """

    code = ConstraintCode.DATE_OUT_OF_RANGE
    version = "1.0.0"

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        # 存放本次规则检测出来的所有违规对象
        violations: list[ConstraintViolation] = []
        # 获取用户原始请求设置的旅行日期范围
        expected_range = context.request.date_range

        # 校验行程整体日期范围是否与用户请求一致
        if itinerary.date_range != expected_range:
            violations.append(
                make_violation(
                    code=self.code,
                    severity=ConstraintSeverity.ERROR,
                    message="行程日期范围与旅行请求不一致",
                    actual={
                        "start_date": itinerary.date_range.start_date,
                        "end_date": itinerary.date_range.end_date,
                    },
                    expected={
                        "start_date": expected_range.start_date,
                        "end_date": expected_range.end_date,
                    },
                    repair_hint="重新按旅行请求日期生成每日计划",
                    rule_version=self.version,
                    discriminator="itinerary-range",
                )
            )

        # 获取行程所使用的时区
        timezone = ZoneInfo(itinerary.timezone)
        for day in itinerary.days:
            for activity in day.activities:
                local_start = activity.start_at.astimezone(timezone)
                local_end = activity.end_at.astimezone(timezone)

                # 判断：活动本地时间 早于行程开始 或者晚于行程结束，判定越界
                if (
                    local_start.date() < expected_range.start_date
                    or local_end.date() > expected_range.end_date
                ):
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"活动“{activity.title}”超出旅行日期范围",
                            actual={
                                "start_at": local_start.isoformat(),
                                "end_at": local_end.isoformat(),
                            },
                            expected={
                                "start_date": expected_range.start_date,
                                "end_date": expected_range.end_date,
                            },
                            repair_hint="移动或删除超出旅行日期的活动",
                            rule_version=self.version,
                        )
                    )

        return violations
