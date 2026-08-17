from datetime import timedelta

from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import ActivityKind, Itinerary


def duration_minutes(value: timedelta) -> float:
    """将时间差换算成分钟，并保留秒级精度。"""
    return value.total_seconds() / 60


class TransferRule:
    """检查交通活动、路线事实和相邻活动之间的衔接关系。

    规则包含以下五部分：
    1. 交通活动必须引用当天存在的路线事实；
    2. 交通活动时长必须覆盖路线预计耗时；
    3. 路线实际出发、到达时间必须落在交通活动时间窗内；
    4. 路线起终点必须与前后活动地点一致；
    5. 前后活动之间必须容纳路线耗时和用户设置的缓冲时间。
    """

    code = ConstraintCode.TRANSFER_TIME_INSUFFICIENT  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """检查行程中的全部交通活动，返回顺序稳定的违规列表。"""
        violations: list[ConstraintViolation] = []
        buffer_limit = context.request.constraints.minimum_transfer_buffer_minutes

        for day in itinerary.days:
            # 先建立索引，避免每检查一个交通活动都遍历一次路线列表。
            route_legs_by_id = {route_leg.id: route_leg for route_leg in day.route_legs}

            for index, transfer in enumerate(day.activities):
                if transfer.kind != ActivityKind.TRANSFER:
                    continue

                route_leg_id = transfer.route_leg_id
                if route_leg_id is None:
                    # Activity 模型通常会提前拒绝该状态，这里保留防御性检查。
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="交通活动没有引用路线事实",
                            actual={"route_leg_id": None},
                            expected={"route_leg_id_present": True},
                            repair_hint="重新查询路线并关联 RouteLeg",
                            rule_version=self.version,
                            discriminator="missing-route-leg-id",
                        )
                    )
                    continue

                route_leg = route_legs_by_id.get(route_leg_id)
                if route_leg is None:
                    # DayPlan 模型也会提前拒绝该状态，但规则不能静默通过。
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="交通活动引用的路线事实不存在",
                            actual={"route_leg_id": str(route_leg_id)},
                            expected={"route_leg_available": True},
                            repair_hint="重新加载路线事实后再检查",
                            rule_version=self.version,
                            discriminator="missing-route-leg",
                        )
                    )
                    continue

                scheduled_minutes = duration_minutes(transfer.end_at - transfer.start_at)
                if scheduled_minutes < route_leg.duration_minutes:
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="交通活动安排的时间短于路线预计耗时",
                            actual={
                                "scheduled_minutes": scheduled_minutes,
                                "route_leg_id": str(route_leg.id),
                            },
                            expected={"minimum_minutes": route_leg.duration_minutes},
                            repair_hint="延长交通活动或调整相邻活动时间",
                            rule_version=self.version,
                            discriminator="route-duration",
                        )
                    )

                if route_leg.departure_time is not None:
                    # RouteLeg 模型保证出发和到达时间成对出现。
                    assert route_leg.arrival_time is not None
                    route_outside_transfer = (
                        route_leg.departure_time < transfer.start_at
                        or route_leg.arrival_time > transfer.end_at
                    )
                    if route_outside_transfer:
                        violations.append(
                            make_violation(
                                code=self.code,
                                severity=ConstraintSeverity.ERROR,
                                day=day.date,
                                activity_id=transfer.id,
                                message="路线实际时间没有完整落在交通活动内",
                                actual={
                                    "route_departure_time": route_leg.departure_time.isoformat(),
                                    "route_arrival_time": route_leg.arrival_time.isoformat(),
                                },
                                expected={
                                    "transfer_start_at": transfer.start_at.isoformat(),
                                    "transfer_end_at": transfer.end_at.isoformat(),
                                },
                                repair_hint="让交通活动完整覆盖路线出发和到达时间",
                                rule_version=self.version,
                                discriminator="route-time-window",
                            )
                        )

                previous = day.activities[index - 1] if index > 0 else None
                following = day.activities[index + 1] if index + 1 < len(day.activities) else None

                if (
                    previous is not None
                    and previous.place_id is not None
                    and previous.place_id != route_leg.origin_place_id
                ):
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="路线起点与前一个活动地点不一致",
                            actual={
                                "previous_place_id": previous.place_id,
                                "route_origin_place_id": route_leg.origin_place_id,
                            },
                            expected={"same_origin_place": True},
                            repair_hint="重新查询正确起点的路线",
                            rule_version=self.version,
                            discriminator="origin-mismatch",
                        )
                    )

                if (
                    following is not None
                    and following.place_id is not None
                    and following.place_id != route_leg.destination_place_id
                ):
                    violations.append(
                        make_violation(
                            code=ConstraintCode.DATA_INCOMPLETE,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="路线终点与后一个活动地点不一致",
                            actual={
                                "following_place_id": following.place_id,
                                "route_destination_place_id": route_leg.destination_place_id,
                            },
                            expected={"same_destination_place": True},
                            repair_hint="重新查询正确终点的路线",
                            rule_version=self.version,
                            discriminator="destination-mismatch",
                        )
                    )

                if previous is None or following is None:
                    # 位于一天开头或结尾时，没有完整的前后活动窗口可检查。
                    continue

                available_minutes = duration_minutes(following.start_at - previous.end_at)
                required_minutes = route_leg.duration_minutes + buffer_limit
                if available_minutes < required_minutes:
                    violations.append(
                        make_violation(
                            code=self.code,
                            severity=ConstraintSeverity.ERROR,
                            day=day.date,
                            activity_id=transfer.id,
                            message="相邻活动之间没有预留足够的交通和缓冲时间",
                            actual={
                                "available_minutes": available_minutes,
                                "route_minutes": route_leg.duration_minutes,
                                "buffer_minutes": (available_minutes - route_leg.duration_minutes),
                            },
                            expected={
                                "minimum_available_minutes": required_minutes,
                                "minimum_buffer_minutes": buffer_limit,
                            },
                            repair_hint="拉开相邻活动时间或选择更快的交通方式",
                            rule_version=self.version,
                            discriminator="activity-window",
                        )
                    )

        return violations
