from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.agent.checkpointer import create_agent_checkpointer
from app.application.clock import Clock
from app.application.facts import FactsFactory
from app.application.repository import TravelRepository


def get_repository(request: Request) -> TravelRepository:
    """从应用状态中获取仓库实例（支持内存与 PostgreSQL/SQLite）。"""
    return request.app.state.repository


def get_clock(request: Request) -> Clock:
    """获取当前时钟实现（生产用系统时钟，测试用固定时钟）。"""
    return request.app.state.clock


def get_facts_factory(request: Request) -> FactsFactory:
    """获取事实工厂，用于把旅行请求转换为规划器只读输入。"""
    return request.app.state.facts_factory


@lru_cache
def get_checkpointer():
    """获取 LangGraph 状态检查点持久化器。"""
    return create_agent_checkpointer()


# FastAPI 依赖别名，路由参数中直接使用 RepositoryDep / ClockDep / FactsFactoryDep
RepositoryDep = Annotated[TravelRepository, Depends(get_repository)]
ClockDep = Annotated[Clock, Depends(get_clock)]
FactsFactoryDep = Annotated[FactsFactory, Depends(get_facts_factory)]
