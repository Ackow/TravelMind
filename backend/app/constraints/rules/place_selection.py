from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


def normalize_place_name(name: str) -> str:
    """按阶段 1 约定去除首尾空格并忽略大小写。"""
    return name.strip().casefold()


class RequiredPlaceRule:
    """检查请求中的每个必去地点是否已经安排进行程。"""

    code = ConstraintCode.REQUIRED_PLACE_MISSING  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """通过地点 ID 解析名称，不进行模糊字符串匹配。"""
        violations: list[ConstraintViolation] = []
        visited_names: set[str] = set()

        for day in itinerary.days:
            for activity in day.activities:
                if activity.place_id is None:
                    continue

                place = context.places_by_id.get(activity.place_id)
                if place is None:
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message="活动引用的地点事实不存在",
                            actual={"place_id": activity.place_id},
                            expected={"place_available": True},
                            repair_hint="加载对应 Place 后重新检查必去地点",
                            rule_version=self.version,
                            discriminator=f"required-missing-place:{activity.place_id}",
                        )
                    )
                    continue

                visited_names.add(normalize_place_name(place.name))
                if place.localized_name:
                    visited_names.add(normalize_place_name(place.localized_name))

        for required_name in context.request.constraints.required_place_names:
            normalized_name = normalize_place_name(required_name)
            if normalized_name in visited_names:
                continue

            violations.append(
                make_violation(
                    code=self.code,
                    severity=ConstraintSeverity.ERROR,
                    message=f"必去地点“{required_name.strip()}”尚未安排进行程",
                    actual={"visited": False},
                    expected={"required_place_name": required_name.strip()},
                    repair_hint="将该地点加入合适日期的活动列表",
                    rule_version=self.version,
                    discriminator=normalized_name,
                )
            )

        return violations


class ExcludedPlaceRule:
    """检查请求明确排除的地点是否错误地出现在行程中。"""

    code = ConstraintCode.EXCLUDED_PLACE_PRESENT  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """定位排除地点首次出现的活动，并返回可直接展示的违规记录。"""
        violations: list[ConstraintViolation] = []
        # 名称映射到首次出现的日期和活动，确保输出顺序及定位结果稳定。
        visited_names: dict[str, tuple] = {}

        for day in itinerary.days:
            for activity in day.activities:
                if activity.place_id is None:
                    continue

                place = context.places_by_id.get(activity.place_id)
                if place is None:
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=activity.id,
                            message="活动引用的地点事实不存在",
                            actual={"place_id": activity.place_id},
                            expected={"place_available": True},
                            repair_hint="加载对应 Place 后重新检查排除地点",
                            rule_version=self.version,
                            discriminator=f"excluded-missing-place:{activity.place_id}",
                        )
                    )
                    continue

                names = [place.name]
                if place.localized_name:
                    names.append(place.localized_name)
                for name in names:
                    visited_names.setdefault(
                        normalize_place_name(name),
                        (day.date, activity),
                    )

        for excluded_name in context.request.constraints.excluded_place_names:
            normalized_name = normalize_place_name(excluded_name)
            occurrence = visited_names.get(normalized_name)
            if occurrence is None:
                continue

            day_date, activity = occurrence
            violations.append(
                make_violation(
                    code=self.code,
                    severity=ConstraintSeverity.ERROR,
                    day=day_date,
                    activity_id=activity.id,
                    message=f"排除地点“{excluded_name.strip()}”出现在行程中",
                    actual={"present": True},
                    expected={"excluded_place_name": excluded_name.strip()},
                    repair_hint="删除该活动或替换为未被排除的地点",
                    rule_version=self.version,
                    discriminator=normalized_name,
                )
            )

        return violations
