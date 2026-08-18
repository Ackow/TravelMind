from datetime import datetime
from app.application.facts import FactsFactory
from app.domain.common import GeoPoint
from app.domain.trip import TripRequest
from app.planning import PlanningFacts
from app.providers.base import PoiProvider, RouteProvider, WeatherProvider
from app.providers.poi.amap import AmapPoiProvider
from app.providers.poi.overpass import OverpassPoiProvider
from app.providers.route.amap import AmapRouteProvider
from app.providers.route.osrm import OSRMRouteProvider
from app.providers.weather.amap import AmapWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.weather.qweather import QWeatherProvider


class CompositeFactsFactory(FactsFactory):
    """支持国内高精度 (高德地点/路线/天气+和风) 与海外全球开源 (OSM+Open-Meteo) 智能双模路由的事实工厂。"""

    def __init__(
        self,
        amap_key: str | None = None,
        qweather_key: str | None = None,
    ) -> None:
        self._amap_key = amap_key
        self._qweather_key = qweather_key

        # 全球开源兜底实例（无需 API Key）
        self._global_weather = OpenMeteoWeatherProvider()
        self._global_poi = OverpassPoiProvider()
        self._global_route = OSRMRouteProvider()

    @staticmethod
    def _is_in_mainland_china(location: GeoPoint) -> bool:
        """粗略地理围栏：经度 73°E~135°E, 纬度 18°N~53.5°N"""
        return 73.0 <= location.longitude <= 135.0 and 18.0 <= location.latitude <= 53.5

    def _resolve_providers(self, location: GeoPoint) -> tuple[WeatherProvider, PoiProvider, RouteProvider]:
        """根据坐标地理围栏与 API Key 自动路由最佳数据源。"""
        is_china = self._is_in_mainland_china(location)

        # 🇨🇳 中国大陆境内且配置了国内 Key -> 使用高德与和风
        if is_china and self._amap_key:
            weather: WeatherProvider = (
                QWeatherProvider(self._qweather_key)
                if self._qweather_key
                else AmapWeatherProvider(self._amap_key)
            )
            poi = AmapPoiProvider(self._amap_key)
            route = AmapRouteProvider(self._amap_key)
            return weather, poi, route

        # 海外城市或无 Key 模式 -> 自动切换全球开源数据源
        return self._global_weather, self._global_poi, self._global_route