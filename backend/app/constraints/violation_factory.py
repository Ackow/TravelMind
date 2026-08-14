import json
from datetime import date
from typing import Any
from uuid import UUID, uuid5

from app.domain.constraints import (
    ConstraintCode,
    ConstraintSeverity,
    ConstraintViolation,
)

VIOLATION_NAMESPACE = UUID("f1870834-c998-4ceb-987f-96a429080001")


def make_violation(
    *,
    code: ConstraintCode,
    severity: ConstraintSeverity,
    message: str,
    rule_version: str,
    day: date | None = None,
    activity_id: UUID | None = None,
    actual: dict[str, Any] | None = None,
    expected: dict[str, Any] | None = None,
    repair_hint: str | None = None,
    discriminator: str = "",
) -> ConstraintViolation:
    """构造约束违规记录的工厂函数
    核心能力：基于违规上下文信息，确定性生成唯一id；相同违规上下文永远得到同一个UUID。
    关键字-only参数：调用必须使用关键字传参，避免参数顺序搞错。
    使用场景：各个约束Rule内部统一调用此函数生成ConstraintViolation对象，不用手动生成id。
    """
    # fingerprint：指纹字符串，把违规关键信息序列化为稳定json
    fingerprint = json.dumps(
        {
            "code": code,
            "day": day.isoformat() if day else None,
            "activity_id": str(activity_id) if activity_id else None,
            "actual": actual,
            "expected": expected,
            "discriminator": discriminator,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return ConstraintViolation(
        id=uuid5(VIOLATION_NAMESPACE, fingerprint),
        code=code,
        severity=severity,
        day=day,
        activity_id=activity_id,
        message=message,
        actual=actual,
        expected=expected,
        repair_hint=repair_hint,
        rule_version=rule_version,
    )
