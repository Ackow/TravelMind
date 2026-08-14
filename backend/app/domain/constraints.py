from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.common import DomainModel


class ConstraintSeverity(StrEnum):
    """约束校验违规严重等级枚举"""

    ERROR = "error"  # 错误，行程不满足硬性约束，必须修复
    WARNING = "warning"  # 警告，不阻断行程，但存在不合理项，建议修复
    INFO = "info"  # 提示，仅作为参考信息展示，无需处理


class ConstraintCode(StrEnum):
    """约束校验违规编码枚举，每一个编码对应一条校验规则"""

    DATE_OUT_OF_RANGE = "DATE_OUT_OF_RANGE"  # 活动时间超出行程日期范围
    ACTIVITY_OVERLAP = "ACTIVITY_OVERLAP"  # 活动时间互相重叠冲突
    PLACE_CLOSED = "PLACE_CLOSED"  # 景点在活动执行日期闭园不可访问
    TRANSFER_TIME_INSUFFICIENT = "TRANSFER_TIME_INSUFFICIENT"  # 转场交通时间不足，前后活动时间冲突
    DAILY_END_TIME_EXCEEDED = "DAILY_END_TIME_EXCEEDED"  # 单日行程结束时间超过允许最晚时间
    MAX_WALKING_EXCEEDED = "MAX_WALKING_EXCEEDED"  # 单日步行距离超过用户设置上限
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"  # 行程总预算超限
    WEATHER_MISMATCH = "WEATHER_MISMATCH"  # 室外活动与天气条件不匹配（如下雨天安排户外景点）
    REQUIRED_PLACE_MISSING = "REQUIRED_PLACE_MISSING"  # 用户指定必去点位未安排进行程
    EXCLUDED_PLACE_PRESENT = "EXCLUDED_PLACE_PRESENT"  # 用户排除的点位出现在行程内
    TOO_MANY_ACTIVITIES = "TOO_MANY_ACTIVITIES"  # 单日活动数量过多，行程过于拥挤
    DATA_INCOMPLETE = "DATA_INCOMPLETE"  # 基础数据缺失，无法完成规划校验


class ConstraintViolation(DomainModel):
    """单条约束违规记录：
    保存某一条规则触发后的全部上下文信息，用于前端展示、自动修复、日志排查
    """

    id: UUID  # 违规记录唯一ID
    code: ConstraintCode  # 违规规则编码
    severity: ConstraintSeverity  # 违规严重等级
    day: date | None = None  # 关联的行程自然日期；全局违规则为None
    activity_id: UUID | None = None  # 关联的活动ID；不属于某个活动的违规置None
    message: str = Field(min_length=1, max_length=500)  # 人类可读的违规描述文本
    actual: dict[str, Any] | None = None  # 实际触发违规的现场数据，用于调试展示
    expected: dict[str, Any] | None = None  # 规则期望的数据标准，与actual做对比
    repair_hint: str | None = Field(
        default=None, min_length=1, max_length=500
    )  # 修复提示文案，指导如何解决该违规
    rule_version: str = Field(min_length=1, max_length=30)  # 校验规则版本号，用于规则迭代兼容


class ConstraintReport(DomainModel):
    """约束校验报告
    行程约束校验完整输出，汇总全部违规项，记录校验元信息，自带业务一致性校验
    """

    passed: bool  # 整体校验是否通过
    violations: list[ConstraintViolation] = Field(default_factory=list)  # 全部违规记录集合
    checked_rule_codes: list[str] = Field(default_factory=list)  # 本次校验执行过的全部规则编码
    checked_at: datetime  # 校验执行时间
    engine_version: str = Field(min_length=1, max_length=30)  # 校验引擎版本

    @model_validator(mode="after")
    def validate_report(self) -> "ConstraintReport":
        """校验报告业务一致性校验器
        1. 校验时间必须携带时区信息
        2. passed字段自动对齐：只要存在ERROR等级违规，passed必须=False；无ERROR则为True
        3. 保证报告内部所有违规ID不重复
        4. 保证被执行的规则编码列表内无重复
        """
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")

        expected_passed = not any(
            item.severity == ConstraintSeverity.ERROR for item in self.violations
        )
        if self.passed != expected_passed:
            raise ValueError("passed must be true exactly when no error exists")

        violation_ids = [item.id for item in self.violations]
        if len(violation_ids) != len(set(violation_ids)):
            raise ValueError("constraint violation ids must be unique")

        if len(self.checked_rule_codes) != len(set(self.checked_rule_codes)):
            raise ValueError("checked_rule_codes must be unique")

        return self
