from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.domain.research import Place
from app.domain.trip import TripRequest


@dataclass(frozen=True, slots=True)
class ConstraintContext:
    """约束规则执行的只读上下文
    所有约束校验规则统一接收该上下文对象，集中提供校验所需全部输入数据
    实例一旦创建，字段不允许修改；checked_at强制要求带时区
    """

    request: TripRequest  # 用户原始行程规划请求
    places_by_id: Mapping[str, Place]  # 点位映射字典
    checked_at: datetime  # 校验时间

    def __post_init__(self) -> None:
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
