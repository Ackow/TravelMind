from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """返回带时区的当前时间。"""


class SystemClock:
    """生产环境使用的系统时钟。"""

    # 返回当前 UTC 时间
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """测试使用的固定时钟。"""

    # 初始化固定时间值
    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError("fixed clock value must be timezone-aware")
        self._value = value

    # 返回固定时间

    def now(self) -> datetime:
        return self._value
