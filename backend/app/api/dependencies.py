from typing import Annotated

from fastapi import Request
from fastapi.params import Depends

from app.application.clock import Clock
from app.application.facts import FactsFactory
from app.application.repository import TravelRepository


def get_repository(request: Request) -> TravelRepository:
    """从应用状态中获取内存/测试仓库。"""
    return request.app.state.repository


def get_clock(request: Request) -> Clock:
    """获取当前时钟实现（生产用系统时钟，测试用固定时钟）。"""
    return request.app.state.clock


def get_facts_factory(request: Request) -> FactsFactory:
    """获取事实工厂，用于把旅行请求转换为规划器只读输入。"""
    return request.app.state.facts_factory


# FastAPI 依赖别名，路由参数中直接使用 RepositoryDep / ClockDep / FactsFactoryDep
RepositoryDep = Annotated[TravelRepository, Depends(get_repository)]
ClockDep = Annotated[Clock, Depends(get_clock)]
FactsFactoryDep = Annotated[FactsFactory, Depends(get_facts_factory)]
