from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 ORM 声明基类"""

    pass


def utc_now() -> datetime:
    """返回标准 UTC 时间戳"""
    return datetime.now(UTC)
