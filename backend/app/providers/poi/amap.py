import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.domain.common import DataQuality, GeoPoint, SourceRef
from app.domain.research import IndoorOutdoor, OpeningPeriod, Place, PlaceCategory
from app.providers.base import PoiProvider, ProviderError, ProviderTimeoutError
from app.providers.coordinates import CoordinateConverter

CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".cache" / "amap"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class AmapPoiProvider(PoiProvider):
    """基于高德开放平台 WebService API 的国内高精度 POI 检索适配器（内置持久化磁盘缓存）。"""

    AROUND_URL = "https://restapi.amap.com/v3/place/around"

    # 高德分类编码前缀映射
    CATEGORY_MAPPING = {
        "110000": PlaceCategory.ATTRACTION,  # 风景名胜
        "140000": PlaceCategory.ATTRACTION,  # 科教文化场所
        "141200": PlaceCategory.MUSEUM,  # 博物馆
        "110101": PlaceCategory.PARK,  # 公园广场
        "110200": PlaceCategory.VIEWPOINT,  # 观景台 / 名胜
        "110202": PlaceCategory.TEMPLE,  # 寺庙道观
        "050000": PlaceCategory.RESTAURANT,  # 餐饮服务
        "050100": PlaceCategory.RESTAURANT,  # 中餐厅
        "050500": PlaceCategory.CAFE,  # 咖啡馆
    }

    def __init__(self, api_key: str, timeout_seconds: float = 6.0) -> None:
        self._key = api_key
        self._timeout = timeout_seconds

    def _map_amap_types(self, typecode: str) -> list[PlaceCategory]:
        for code, cat in self.CATEGORY_MAPPING.items():
            if typecode.startswith(code):
                return [cat]

        return [PlaceCategory.ATTRACTION]

    def search_places(
        self,
        *,
        destination: str,
        location: GeoPoint,
        categories: list[PlaceCategory] | None = None,
        limit: int = 20,
    ) -> list[Place]:
        # 1. 将 WGS-84 坐标转换为高德火星坐标
        gcj_loc = CoordinateConverter.wgs84_to_gcj02(location)

        # 2. 检查本地磁盘持久化缓存，避免重复调用浪费 API 配额
        cache_key = hashlib.md5(
            f"poi_{destination}_{gcj_loc.longitude:.4f}_{gcj_loc.latitude:.4f}_{limit}".encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"poi_{cache_key}.json"

        data: dict | None = None
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                data = None

        if data is None:
            # 3. 请求高德周边 POI API (方圆 8000 米，涵盖景点与特色餐饮)
            params = {
                "key": self._key,
                "location": f"{gcj_loc.longitude:.6f},{gcj_loc.latitude:.6f}",
                "types": "110000|140000|050000",
                "radius": 8000,
                "offset": limit,
                "page": 1,
                "extensions": "all",
            }

            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.get(self.AROUND_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(
                    "高德 POI 检索超时", provider_name="amap", cause=exc
                ) from exc
            except Exception as exc:
                raise ProviderError(
                    f"高德 POI 请求失败: {exc}", provider_name="amap", cause=exc
                ) from exc

            if data.get("status") != "1":
                raise ProviderError(f"高德 API 返回错误: {data.get('info')}", provider_name="amap")

            try:
                cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        if data.get("status") != "1":
            raise ProviderError(f"高德 API 返回错误: {data.get('info')}", provider_name="amap")

        pois = data.get("pois", [])
        places: list[Place] = []
        now_dt = datetime.now(UTC)

        for item in pois:
            name = item.get("name")
            location_str = item.get("location", "")
            if not name or not location_str or "," not in location_str:
                continue

            lon_str, lat_str = location_str.split(",")
            # 3. 将高德返回的 GCJ-02 坐标还原为领域标准 WGS-84 坐标
            raw_gcj = GeoPoint(latitude=float(lat_str), longitude=float(lon_str))
            std_wgs = CoordinateConverter.gcj02_to_wgs84(raw_gcj)

            typecode = item.get("typecode", "")
            cats = self._map_amap_types(typecode)
            is_indoor = (
                IndoorOutdoor.INDOOR
                if PlaceCategory.MUSEUM in cats or PlaceCategory.RESTAURANT in cats
                else IndoorOutdoor.OUTDOOR
            )

            rating_raw = item.get("biz_ext", {}).get("rating")
            rating = float(rating_raw) if rating_raw and rating_raw != [] else 4.6

            # 默认营业时间 09:00 ~ 18:00
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
                    id=f"amap_{item.get('id')}",
                    name=name,
                    localized_name=name,
                    categories=cats,
                    address=item.get("address") or destination,
                    location=std_wgs,
                    rating=rating,
                    estimated_visit_minutes=90 if PlaceCategory.MUSEUM in cats else 60,
                    indoor_outdoor=is_indoor,
                    opening_periods=default_periods,
                    tags=[item.get("type", "")] if item.get("type") else [],
                    source=SourceRef(
                        provider="amap",
                        source_id=item.get("id"),
                        source_url="https://ditu.amap.com",
                        fetched_at=now_dt,
                        data_quality=DataQuality.VERIFIED,
                    ),
                )
            )

        return places

    def get_place_detail(self, *, place_id: str) -> Place | None:
        return None
