from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 ORM 声明基类"""
    pass


def utc_now() -> datetime:
    """返回标准 UTC 时间戳"""
    return datetime.now(timezone.utc)