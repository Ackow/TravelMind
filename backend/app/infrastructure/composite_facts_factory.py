from datetime import datetime

from app.application.facts import FactsFactory
from app.core.config import get_settings
from app.domain.common import DataQuality, GeoPoint, SourceRef
from app.domain.itinerary import ExchangeRate
from app.domain.trip import TransportMode, TripRequest
from app.fixtures.loader import load_tokyo_places, load_tokyo_weather
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
        settings = get_settings()
        self._amap_key = amap_key or settings.AMAP_API_KEY
        self._qweather_key = qweather_key or settings.QWEATHER_API_KEY

        # 全球开源兜底实例（无需 API Key）
        self._global_weather = OpenMeteoWeatherProvider()
        self._global_poi = OverpassPoiProvider()
        self._global_route = OSRMRouteProvider()

    @staticmethod
    def _is_in_mainland_china(location: GeoPoint) -> bool:
        """粗略地理围栏：经度 73°E~135°E, 纬度 18°N~53.5°N"""
        return 73.0 <= location.longitude <= 135.0 and 18.0 <= location.latitude <= 53.5

    def _resolve_providers(
        self, location: GeoPoint
    ) -> tuple[WeatherProvider, PoiProvider, RouteProvider]:
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

    def build(self, request: TripRequest, planned_at: datetime) -> PlanningFacts:
        """根据 TripRequest 聚合多源事实并构建 PlanningFacts 只读快照。"""
        dest_lower = request.destination.strip().lower()
        if "tokyo" in dest_lower or "东京" in dest_lower:
            center = GeoPoint(latitude=35.6895, longitude=139.6917)
        elif "nanjing" in dest_lower or "南京" in dest_lower:
            center = GeoPoint(latitude=32.0603, longitude=118.7969)
        elif "beijing" in dest_lower or "北京" in dest_lower:
            center = GeoPoint(latitude=39.9042, longitude=116.4074)
        elif "shanghai" in dest_lower or "上海" in dest_lower:
            center = GeoPoint(latitude=31.2304, longitude=121.4737)
        elif "kyoto" in dest_lower or "京都" in dest_lower:
            center = GeoPoint(latitude=35.0116, longitude=135.7681)
        elif "osaka" in dest_lower or "大阪" in dest_lower:
            center = GeoPoint(latitude=34.6937, longitude=135.5023)
        else:
            center = GeoPoint(latitude=35.6895, longitude=139.6917)

        weather_prov, poi_prov, route_prov = self._resolve_providers(center)

        # 1. 抓取多日天气
        try:
            weather_days = weather_prov.get_forecast(
                location=center,
                start_date=request.date_range.start_date,
                end_date=request.date_range.end_date,
            )
        except Exception:
            weather_days = list(load_tokyo_weather())

        # 2. 检索周边 POI 并融合城市基准景点库
        known_places = (
            list(load_tokyo_places()) if ("tokyo" in dest_lower or "东京" in dest_lower) else []
        )
        try:
            live_places = poi_prov.search_places(
                destination=request.destination,
                location=center,
                limit=15,
            )
        except Exception:
            live_places = []

        all_places_map = {p.id: p for p in known_places}
        for p in live_places:
            if p.id not in all_places_map:
                all_places_map[p.id] = p
        places = list(all_places_map.values())
        if not places:
            places = list(load_tokyo_places())

        # 3. 计算路线矩阵
        place_coords = [(p.id, p.location) for p in places[:10]]
        mode = (
            request.preferences.transport_modes[0]
            if request.preferences.transport_modes
            else TransportMode.PUBLIC_TRANSIT
        )
        try:
            route_matrix = route_prov.calculate_matrix(
                locations=place_coords,
                mode=mode,
            )
        except Exception:
            from app.fixtures.loader import load_tokyo_route_matrix

            route_matrix = load_tokyo_route_matrix()

        # 4. 汇率
        source = SourceRef(
            provider="composite",
            source_id="default-exchange",
            fetched_at=planned_at,
            data_quality=DataQuality.ESTIMATED,
        )
        rate = ExchangeRate(
            from_currency="JPY" if ("tokyo" in dest_lower or "东京" in dest_lower) else "CNY",
            to_currency=request.display_currency,
            rate=1.0 if request.display_currency == "CNY" else 4.8,
            fetched_at=planned_at,
            source=source,
        )

        return PlanningFacts(
            request=request,
            places=tuple(places),
            weather=tuple(weather_days),
            route_matrix=route_matrix,
            exchange_rates={"JPY/CNY": rate},
            planned_at=planned_at,
        )
