from app.constraints.context import ConstraintContext
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary


class BudgetRule:
    """检查总预算上限和每日费用统计的一致性。

    金额使用 Money.amount 的最小货币单位整数比较。不同币种不能直接计算，
    必须先补齐换汇结果；本规则不会自行创造“平均每日预算上限”。
    """

    code = ConstraintCode.BUDGET_EXCEEDED  # 规则编码
    version = "1.0.0"  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """返回总预算超限和每日费用统计不一致的违规记录。"""
        violations: list[ConstraintViolation] = []
        actual = itinerary.budget.planned_total
        limit = context.request.constraints.total_budget

        if actual.currency != limit.currency:
            # 币种不一致时数值没有可比性，不能继续判断是否超预算。
            violations.append(
                make_violation(
                    code=ConstraintCode.DATA_INCOMPLETE,
                    severity=ConstraintSeverity.ERROR,
                    message="计划总额与请求预算的币种不一致",
                    actual={"planned_currency": actual.currency},
                    expected={"budget_currency": limit.currency},
                    repair_hint="先按有效汇率换算为请求预算币种",
                    rule_version=self.version,
                    discriminator="budget-currency",
                )
            )
        elif actual.amount > limit.amount:
            # 软预算仍需要提示，但不会导致整份约束报告失败。
            severity = (
                ConstraintSeverity.ERROR
                if context.request.constraints.budget_is_hard_limit
                else ConstraintSeverity.WARNING
            )
            violations.append(
                make_violation(
                    code=self.code,
                    severity=severity,
                    message="行程计划总额超过用户预算",
                    actual={
                        "planned_amount": actual.amount,
                        "currency": actual.currency,
                    },
                    expected={"maximum_amount": limit.amount},
                    repair_hint="减少高费用项目或提高总预算",
                    rule_version=self.version,
                    discriminator="total-budget",
                )
            )

        for day in itinerary.days:
            # 预算明细是费用事实来源，按日期重新汇总后与 DayStatistics 比较。
            expected_daily_amount = sum(
                item.amount.amount for item in itinerary.budget.items if item.date == day.date
            )
            daily_cost = day.statistics.estimated_cost

            if daily_cost.currency != itinerary.budget.currency:
                violations.append(
                    make_violation(
                        code=ConstraintCode.DATA_INCOMPLETE,
                        severity=ConstraintSeverity.WARNING,
                        day=day.date,
                        message="单日费用统计与预算汇总的币种不一致",
                        actual={"statistics_currency": daily_cost.currency},
                        expected={"budget_currency": itinerary.budget.currency},
                        repair_hint="将单日统计换算为预算汇总币种",
                        rule_version=self.version,
                        discriminator="daily-cost-currency",
                    )
                )
                continue

            if daily_cost.amount != expected_daily_amount:
                violations.append(
                    make_violation(
                        code=ConstraintCode.DATA_INCOMPLETE,
                        severity=ConstraintSeverity.WARNING,
                        day=day.date,
                        message="单日费用统计与预算明细不一致",
                        actual={"statistics_amount": daily_cost.amount},
                        expected={"budget_items_amount": expected_daily_amount},
                        repair_hint="根据当天预算明细重新计算 DayStatistics",
                        rule_version=self.version,
                        discriminator="daily-cost-statistics",
                    )
                )

        return violations
