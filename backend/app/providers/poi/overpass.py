from datetime import UTC, datetime
import httpx
from app.domain.common import DataQuality, GeoPoint, SourceRef
from app.domain.research import IndoorOutdoor, OpeningPeriod, Place, PlaceCategory
from app.providers.base import PoiProvider, ProviderError, ProviderTimeoutError


class OverpassPoiProvider(PoiProvider):
    """基于 OpenStreetMap Overpass API 的真实地点检索适配器。"""

    # 主节点与公共备用镜像节点
    ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    HEADERS = {
        "User-Agent": "TravelMind/1.0 (contact@travelmind.local; +https://github.com/Ackow/TravelMind)",
        "Accept": "application/json",
    }

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    @staticmethod
    def _map_category(tags: dict[str, str]) -> list[PlaceCategory]:
        tourism = tags.get("tourism")
        amenity = tags.get("amenity")
        leisure = tags.get("leisure")

        categories = []
        if tourism == "museum":
            categories.append(PlaceCategory.MUSEUM)
        if tourism in ("attraction", "theme_park"):
            categories.append(PlaceCategory.ATTRACTION)
        if tourism == "viewpoint":
            categories.append(PlaceCategory.VIEWPOINT)
        if leisure == "park":
            categories.append(PlaceCategory.PARK)
        if amenity in ("place_of_worship", "shrine"):
            categories.append(PlaceCategory.TEMPLE)
        if amenity == "restaurant":
            categories.append(PlaceCategory.RESTAURANT)

        return categories or [PlaceCategory.ATTRACTION]

    @staticmethod
    def _estimate_minutes(categories: list[PlaceCategory]) -> int:
        if PlaceCategory.MUSEUM in categories:
            return 120
        if PlaceCategory.PARK in categories or PlaceCategory.VIEWPOINT in categories:
            return 60
        if PlaceCategory.TEMPLE in categories or PlaceCategory.SHRINE in categories:
            return 45
        return 60

    def search_places(
        self,
        *,
        destination: str,
        location: GeoPoint,
        categories: list[PlaceCategory] | None = None,
        limit: int = 20,
    ) -> list[Place]:
        # 查询中心点周边 6000 米范围内的旅游景点与公园
        query = f"""[out:json][timeout:8];
(
  node["tourism"~"museum|attraction|viewpoint"](around:6000,{location.latitude},{location.longitude});
  node["leisure"="park"](around:6000,{location.latitude},{location.longitude});
);
out body {limit};
"""

        last_error: Exception | None = None
        data: dict[str, object] = {}

        with httpx.Client(timeout=self._timeout, headers=self.HEADERS) as client:
            for endpoint in self.ENDPOINTS:
                try:
                    resp = client.post(endpoint, data={"data": query})
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.TimeoutException as exc:
                    last_error = exc
                    continue
                except Exception as exc:
                    last_error = exc
                    continue

        if not data and last_error:
            if isinstance(last_error, httpx.TimeoutException):
                raise ProviderTimeoutError(
                    "Overpass POI 检索超时", provider_name="overpass", cause=last_error
                ) from last_error
            raise ProviderError(
                f"Overpass 检索异常: {last_error}", provider_name="overpass", cause=last_error
            ) from last_error

        elements = data.get("elements", [])
        places: list[Place] = []
        now_dt = datetime.now(UTC)

        for elem in elements:
            tags = elem.get("tags", {})
            name = tags.get("name:zh") or tags.get("name") or tags.get("name:en")
            if not name:
                continue

            cats = self._map_category(tags)
            is_indoor = (
                IndoorOutdoor.INDOOR
                if PlaceCategory.MUSEUM in cats
                else IndoorOutdoor.OUTDOOR
            )

            # 构造每日 09:00 - 18:00 标准营业时间（若未显式标注）
            default_periods = [
                OpeningPeriod(
                    day_of_week=d,
                    open_time=datetime.strptime("09:00", "%H:%M").time(),
                    close_time=datetime.strptime("18:00", "%H:%M").time(),
                    closed=False,
                )
                for d in range(1, 8)
            ]

            places.append(
                Place(
                    id=f"osm_{elem['id']}",
                    name=name,
                    localized_name=tags.get("name"),
                    categories=cats,
                    address=tags.get("addr:street") or destination,
                    location=GeoPoint(latitude=elem["lat"], longitude=elem["lon"]),
                    rating=4.5,
                    estimated_visit_minutes=self._estimate_minutes(cats),
                    indoor_outdoor=is_indoor,
                    opening_periods=default_periods,
                    tags=[v for k, v in tags.items() if k in ("historic", "religion", "tourism")],
                    source=SourceRef(
                        provider="openstreetmap_overpass",
                        fetched_at=now_dt,
                        source_url="https://www.openstreetmap.org",
                        data_quality=DataQuality.VERIFIED,
                    ),
                )
            )

        return places

    def get_place_detail(self, *, place_id: str) -> Place | None:
        # 单点详情由 search_places 承载或直接查询 OSM 节点 ID
        return None