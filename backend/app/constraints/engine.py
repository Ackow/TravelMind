from collections.abc import Iterable, Sequence

from app.constraints.context import ConstraintContext
from app.constraints.rule import ConstraintRule
from app.domain.constraints import (
    ConstraintCode,
    ConstraintReport,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary

ENGINE_VERSION = "1.0.0"

SEVERITY_ORDER = {
    ConstraintSeverity.ERROR: 0,
    ConstraintSeverity.WARNING: 1,
    ConstraintSeverity.INFO: 2,
}


def violation_sort_key(item: ConstraintViolation) -> tuple:
    """违规记录排序key函数
    排序优先级：
    1. 严重程度（ERROR排最前面）
    2. 发生日期，无日期的全局违规排最前
    3. 违规code枚举值
    4. 活动ID
    5. violation唯一id（兜底，保证排序稳定）
    """
    return (
        SEVERITY_ORDER[item.severity],
        item.day.isoformat() if item.day else "",
        item.code.value,
        str(item.activity_id or ""),
        str(item.id),
    )


class ConstraintEngine:
    """约束校验引擎核心
    职责：管理全部校验规则、支持筛选部分规则执行、批量运行规则、收集违规、排序、生成最终校验报告ConstraintReport
    """

    def __init__(self, rules: Sequence[ConstraintRule]) -> None:
        """初始化约束引擎并校验规则编码唯一。"""
        codes = [rule.code for rule in rules]
        # 校验：不允许出现重复的rule.code，一个编码只能对应一条规则
        if len(codes) != len(set(codes)):
            raise ValueError("constraint rule codes must be unique")
        self._rules = tuple(rules)

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
        rule_codes: Iterable[ConstraintCode] | None = None,
    ) -> ConstraintReport:
        """执行约束校验入口"""

        # 如果传入指定规则编码，转为集合方便快速查找；None代表不做过滤
        selected_codes = set(rule_codes) if rule_codes is not None else None

        # 筛选待执行的规则
        selected_rules = [
            rule for rule in self._rules if selected_codes is None or rule.code in selected_codes
        ]

        # 遍历选中的每一条规则，调用check，把所有规则产出的violation平铺到一个列表
        violations = [
            violation for rule in selected_rules for violation in rule.check(itinerary, context)
        ]

        # 使用自定义key对违规列表排序
        violations.sort(key=violation_sort_key)

        # 获取本次实际执行过的所有规则编码，排序后存入报告，便于追溯
        checked_rule_codes = sorted(
            {rule.code for rule in selected_rules},
            key=lambda code: code.value,
        )

        # 判断行程是否校验通过
        passed = not any(item.severity == ConstraintSeverity.ERROR for item in violations)

        # 组装并返回报告对象
        return ConstraintReport(
            passed=passed,  # 是否校验通过
            violations=violations,  # 已排序全部违规
            checked_rule_codes=checked_rule_codes,  # 本次执行了哪些规则
            checked_at=context.checked_at,  # 使用固定上下文时间，保证结果可复现
            engine_version=ENGINE_VERSION,  # 引擎版本
        )
