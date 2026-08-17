from typing import Protocol

from app.constraints.context import ConstraintContext
from app.domain.constraints import ConstraintCode, ConstraintViolation
from app.domain.itinerary import Itinerary


class ConstraintRule(Protocol):
    """约束规则协议（接口定义）
    所有实现该协议的约束规则类，必须拥有 code、version 属性以及 check() 方法。
    作用：统一所有校验规则的接口，方便引擎批量调用、管理全部约束规则。
    """

    code: ConstraintCode  # 规则编码
    version: str  # 规则版本

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        """执行约束校验并返回违规列表。"""
