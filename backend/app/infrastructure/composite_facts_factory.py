from datetime import date
from app.application.facts import FactsFactory
from app.domain.common import DateRange, GeoPoint
from app.domain.research import Place, RouteMatrixCell, WeatherDay
from app.domain.trip import TransportMode
from app.providers.base import PoiProvider, RouteProvider, WeatherProvider
from app.providers.decorators import InMemoryTTLCache


class CompositeFactsFactory(FactsFactory):
    """生产级事实工厂：集成真实数据 Provider 与 TTL 防腐缓存。"""

    def __init__(
        self,
        weather_provider: WeatherProvider,
        poi_provider: PoiProvider,
        route_provider: RouteProvider,
    ) -> None:
        self._weather = weather_provider
        self._poi = poi_provider
        self._route = route_provider
        self._cache = InMemoryTTLCache(default_ttl_seconds=600)

    def get_weather_forecast(self, destination: str, date_range: DateRange) -> list[WeatherDay]:
        cache_key = f"weather:{destination}:{date_range.start_date}:{date_range.end_date}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # 默认使用目的地中心坐标
        tokyo_center = GeoPoint(latitude=35.6762, longitude=139.6503)
        res = self._weather.get_forecast(destination=destination, location=tokyo_center, date_range=date_range)
        self._cache.set(cache_key, res)
        return res

    def get_candidate_places(self, destination: str) -> list[Place]:
        cache_key = f"places:{destination}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        tokyo_center = GeoPoint(latitude=35.6762, longitude=139.6503)
        res = self._poi.search_places(destination=destination, location=tokyo_center, limit=20)
        self._cache.set(cache_key, res)
        return res

    def get_route_matrix(
        self,
        origin_place_ids: list[str],
        destination_place_ids: list[str],
        mode: TransportMode,
    ) -> list[RouteMatrixCell]:
        places = {p.id: p.location for p in self.get_candidate_places("Tokyo")}
        origins = [(pid, places[pid]) for pid in origin_place_ids if pid in places]
        destinations = [(pid, places[pid]) for pid in destination_place_ids if pid in places]

        return self._route.get_route_matrix(origins=origins, destinations=destinations, mode=mode)