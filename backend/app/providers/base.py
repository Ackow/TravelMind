from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.common import DateRange, GeoPoint
from app.domain.research import Place, PlaceCategory, RouteMatrixCell, WeatherDay
from app.domain.trip import TransportMode


class ProviderError(Exception):
    """外部数据提供商通用异常基类。"""

    def __init__(
        self,
        message: str,
        *,
        provider_name: str,
        recoverable: bool = True,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(f"[{provider_name}] {message}")
        self.provider_name = provider_name
        self.recoverable = recoverable
        self.cause = cause


class ProviderTimeoutError(ProviderError):
    """请求第三方 API 超时。"""


class ProviderRateLimitError(ProviderError):
    """触发第三方 API 频控与限流。"""


class ProviderNotFoundError(ProviderError):
    """查询的城市或地点不存在。"""


@runtime_checkable
class WeatherProvider(Protocol):
    """天气预报数据提供商协议。"""

    def get_forecast(
        self,
        *,
        destination: str,
        location: GeoPoint,
        date_range: DateRange,
    ) -> list[WeatherDay]:
        """获取指定地点在出行日期内的逐日天气。"""
        ...


@runtime_checkable
class PoiProvider(Protocol):
    """地点与兴趣点数据提供商协议。"""

    def search_places(
        self,
        *,
        destination: str,
        location: GeoPoint,
        categories: list[PlaceCategory] | None = None,
        limit: int = 20
    ) -> list[Place]:
        """检索目的地的候选游玩地点。"""
        ...

    def get_place_detail(self, *, place_id: str) -> Place | None:
        """获取单个地点的详细营业时间与属性。"""
        ...


@runtime_checkable
class RouteProvider(Protocol):
    """交通耗时与路线距离提供商协议。"""

    def get_route_matrix(
        self,
        *,
        origins: list[tuple[str, GeoPoint]],  # (place_id, location)
        destinations: list[tuple[str, GeoPoint]],
        mode: TransportMode,
    ) -> list[RouteMatrixCell]:
        """批量获取起点与终点之间的通行耗时矩阵。"""
        ...