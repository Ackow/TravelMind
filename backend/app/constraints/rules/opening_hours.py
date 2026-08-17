from datetime import time
from zoneinfo import ZoneInfo

from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import ActivityKind, Itinerary
from app.domain.research import OpeningPeriod, Place, SpecialOpeningPeriod

# 营业时间类型联合：普通周营业时间 / 特殊节假日开闭时间
OpeningValue = OpeningPeriod | SpecialOpeningPeriod


def find_opening_value(place: Place, target_date) -> OpeningValue | None:
    """获取地点在目标日期生效的营业时间

    优先级：特殊开闭日期（节假日/临时闭馆） > 常规星期营业时间
    """
    # 优先匹配特殊开闭周期
    for period in place.special_opening_periods:
        if period.date == target_date:
            return period

    # 按星期匹配常规营业时间
    weekday = target_date.isoweekday()
    for period in place.opening_periods:
        if period.day_of_week == weekday:
            return period

    return None


def local_clock(value, timezone: ZoneInfo) -> time:
    return value.astimezone(timezone).time().replace(tzinfo=None)


class OpeningHoursRule:
    """景点营业时间校验规则
    校验VISIT参观类活动：
    1. 点位基础数据缺失（places_by_id找不到place）→ DATA_INCOMPLETE ERROR
    2. 找不到当天任何营业时间数据 → DATA_INCOMPLETE WARNING
    3. 该日明确闭馆 → PLACE_CLOSED ERROR
    4. 活动时间超出当日开放时段 → PLACE_CLOSED ERROR
    """

    code = ConstraintCode.PLACE_CLOSED  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        timezone = ZoneInfo(itinerary.timezone)

        for day in itinerary.days:
            for activity in day.activities:
                # 只处理【参观VISIT】类型活动；非参观活动 / 无place_id直接跳过
                if activity.kind != ActivityKind.VISIT or activity.place_id is None:
                    continue

                place = context.places_by_id.get(activity.place_id)
                if place is None:
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"找不到活动“{activity.title}”引用的地点事实",
                            actual={"place_id": activity.place_id},
                            expected={"place_fact_available": True},
                            repair_hint="重新加载地点详情后再检查",
                            rule_version=self.version,
                            discriminator="missing-place",
                        )
                    )
                    continue

                # 查询该地点在这一天生效的营业时间（特殊优先，其次周常规）
                period = find_opening_value(place, day.date)
                if period is None:
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.WARNING,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"地点“{place.name}”缺少当天营业时间",
                            actual={"opening_period": None},
                            expected={"opening_period_available": True},
                            repair_hint="获取地点当天营业时间后再次检查",
                            rule_version=self.version,
                            discriminator="missing-opening-hours",
                        )
                    )
                    continue

                # 判断：当天明确标记闭馆（特殊闭馆日、每周休息日）
                if period.closed:
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"地点“{place.name}”当天闭馆",
                            actual={"closed": True},
                            expected={"closed": False},
                            repair_hint="改到开放日期或替换为其他地点",
                            rule_version=self.version,
                            discriminator="explicitly-closed",
                        )
                    )
                    continue

                start_time = local_clock(activity.start_at, timezone)
                end_time = local_clock(activity.end_at, timezone)
                assert period.open_time is not None
                assert period.close_time is not None

                # 校验：活动开始早于开门时间 或者 活动结束晚于关门时间
                if start_time < period.open_time or end_time > period.close_time:
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"活动“{activity.title}”不在营业时间内",
                            actual={
                                "start_time": start_time,
                                "end_time": end_time,
                            },
                            expected={
                                "open_time": period.open_time,
                                "close_time": period.close_time,
                            },
                            repair_hint="将活动完整移动到营业时间范围内",
                            rule_version=self.version,
                            discriminator="outside-opening-hours",
                        )
                    )

        return violations
