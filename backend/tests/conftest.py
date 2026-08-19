"""Pytest 全局配置与数据隔离 Fixtures。

确保所有测试只在独立测试数据库（travelmind_test_db）或独立临时 SQLite 中运行，
彻底避免测试数据与生产/开发库（travelmind_db）混合。
"""
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings
from app.infrastructure.sql_repository import SqlAlchemyTravelRepository
from app.persistence.base import Base


@pytest.fixture(scope="session")
def test_postgres_engine():
    """连接独立的测试数据库 travelmind_test_db，并在测试会话级初始化 Schema。"""
    settings = get_settings()
    test_db_url = settings.TEST_DATABASE_URL
    try:
        engine = create_engine(test_db_url, echo=False)
        Base.metadata.create_all(engine)
        yield engine
    except Exception as exc:
        pytest.skip(f"无法连接测试数据库 travelmind_test_db，跳过 PostgreSQL 测试: {exc}")


@pytest.fixture
def postgres_repo(test_postgres_engine) -> Generator[SqlAlchemyTravelRepository, None, None]:
    """为每个测试用例提供干净隔离的 PostgreSQL 仓储，测试结束后自动清理测试数据。"""
    session_factory = sessionmaker(bind=test_postgres_engine, expire_on_commit=False)
    repo = SqlAlchemyTravelRepository(session_factory)
    
    yield repo
    
    # 清理用例产生的测试数据，保证测试间互不干扰
    with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture
def sqlite_repo(tmp_path) -> SqlAlchemyTravelRepository:
    """创建完全隔离的临时 SQLite 数据库仓储。"""
    db_file = tmp_path / "isolated_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine)
    return SqlAlchemyTravelRepository(session_factory)
