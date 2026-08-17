from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import ActivityKind, Itinerary
from app.domain.research import IndoorOutdoor, OutdoorSuitability


class WeatherCompatibilityRule:
    """检查游览活动的室内外属性是否适合当天的天气。

    恶劣天气下，纯室外游览产生错误，室内外混合游览产生警告；缺少天气
    数据时产生数据不完整警告。交通、入住等结构性活动不参与天气判断。
    """

    code = ConstraintCode.WEATHER_MISMATCH  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """返回需要调整日期或更换室内地点的游览活动。"""
        violations: list[ConstraintViolation] = []

        for day in itinerary.days:
            visits = [
                activity for activity in day.activities if activity.kind == ActivityKind.VISIT
            ]
            if not visits:
                continue

            if day.weather is None:
                # 对每个受影响活动报告一次，便于前端精确定位和后续修复。
                for activity in visits:
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.WARNING,
                            day=day.date,
                            activity_id=activity.id,
                            message=f"缺少活动“{activity.title}”所在日期的天气数据",
                            actual={"weather": None},
                            expected={"weather_available": True},
                            repair_hint="加载当天的天气预报后重新检查",
                            rule_version=self.version,
                            discriminator="missing-weather",
                        )
                    )
                continue

            if day.weather.outdoor_suitability != OutdoorSuitability.POOR:
                continue

            for activity in visits:
                if activity.indoor_outdoor == IndoorOutdoor.OUTDOOR:
                    severity = ConstraintSeverity.ERROR
                elif activity.indoor_outdoor == IndoorOutdoor.MIXED:
                    severity = ConstraintSeverity.WARNING
                else:
                    # 室内或属性未知的活动不被武断判为天气冲突。
                    continue

                violations.append(
                    make_violation(
                        code=self.code,
                        severity=severity,
                        day=day.date,
                        activity_id=activity.id,
                        message=f"活动“{activity.title}”与当天恶劣天气不兼容",
                        actual={
                            "outdoor_suitability": day.weather.outdoor_suitability,
                            "activity_type": activity.indoor_outdoor,
                        },
                        expected={"preferred_activity_type": IndoorOutdoor.INDOOR},
                        repair_hint="替换为室内地点或移动到天气较好的日期",
                        rule_version=self.version,
                    )
                )

        return violations
