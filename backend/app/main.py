from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.v1 import api_v1_router
from app.application.clock import Clock, SystemClock
from app.application.facts import FactsFactory
from app.application.repository import TravelRepository
from app.core.config import get_settings
from app.infrastructure.memory_repository import InMemoryTravelRepository
from app.infrastructure.nanjing_facts_factory import NanjingFactsFactory


def get_default_facts_factory() -> FactsFactory:
    settings = get_settings()
    if settings.USE_MCP_TOOLS:
        from app.infrastructure.mcp_facts_factory import McpFactsFactory

        return McpFactsFactory()
    if settings.DATA_PROVIDER_MODE == "live":
        from app.infrastructure.composite_facts_factory import CompositeFactsFactory

        return CompositeFactsFactory()
    return NanjingFactsFactory()


def create_app(
    *,
    repository: TravelRepository | None = None,
    clock: Clock | None = None,
    facts_factory: FactsFactory | None = None,
) -> FastAPI:
    """创建 FastAPI 应用实例。

    支持通过依赖注入替换默认的内存仓库、时钟和事实工厂，便于测试与扩展。
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="TravelMind dynamic travel planning agent API",
    )
    # 将核心依赖挂到 app.state，路由层通过 Depends 获取
    if repository is not None:
        application.state.repository = repository
    elif settings.USE_SQL_REPOSITORY:
        from app.core.database import SessionLocal
        from app.infrastructure.sql_repository import SqlAlchemyTravelRepository

        application.state.repository = SqlAlchemyTravelRepository(SessionLocal)
    else:
        application.state.repository = InMemoryTravelRepository()

    application.state.clock = clock or SystemClock()
    application.state.facts_factory = facts_factory or get_default_facts_factory()

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # 为每个请求生成/透传 request_id，方便日志串联和问题排查
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # 注册统一异常处理（业务异常 + 参数校验异常）
    install_error_handlers(application)

    # 配置跨域：前端开发地址可访问，并暴露自定义响应头
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Location", "ETag", "X-Request-ID"],
    )

    # 注册所有 API v1 路由
    application.include_router(api_v1_router)

    return application


app = create_app()
