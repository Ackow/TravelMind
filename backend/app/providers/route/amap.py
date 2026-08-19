import httpx

from app.domain.common import GeoPoint, Money
from app.domain.research import RouteMatrixCell, RouteMatrixStatus
from app.domain.trip import TransportMode
from app.providers.base import RouteProvider
from app.providers.coordinates import CoordinateConverter
from app.providers.route.osrm import haversine_distance_meters


class AmapRouteProvider(RouteProvider):
    """基于高德 Distance / Direction 的国内路线与真实公交换乘适配器。"""

    DISTANCE_URL = "https://restapi.amap.com/v3/distance"

    def __init__(self, api_key: str, timeout_seconds: float = 6.0) -> None:
        self._key = api_key
        self._timeout = timeout_seconds

    def get_route_matrix(
        self,
        *,
        origins: list[tuple[str, GeoPoint]],
        destinations: list[tuple[str, GeoPoint]],
        mode: TransportMode,
    ) -> list[RouteMatrixCell]:
        if not origins or not destinations:
            return []

        # 转换为高德火星坐标格式: "lon1,lat1|lon2,lat2"
        origins_gcj = [CoordinateConverter.wgs84_to_gcj02(pt) for _, pt in origins]
        dest_gcj = [CoordinateConverter.wgs84_to_gcj02(pt) for _, pt in destinations]

        orig_str = "|".join(f"{pt.longitude:.6f},{pt.latitude:.6f}" for pt in origins_gcj)
        dest_str = "|".join(f"{pt.longitude:.6f},{pt.latitude:.6f}" for pt in dest_gcj)

        # 高德 type: 1-驾车距离与时间, 3-步行距离与时间
        type_val = "3" if mode == TransportMode.WALKING else "1"
        params = {
            "key": self._key,
            "origins": orig_str,
            "destination": dest_str,
            "type": type_val,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(self.DISTANCE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            # 高德异常时自动降级为直线距离
            return self._fallback_haversine(origins, destinations, mode)

        results = data.get("results", [])
        cells: list[RouteMatrixCell] = []

        for i, (orig_id, _) in enumerate(origins):
            for j, (dest_id, _) in enumerate(destinations):
                idx = i * len(destinations) + j
                res_item = results[idx] if idx < len(results) else {}

                duration_sec = int(res_item.get("duration", 900))
                distance_m = int(res_item.get("distance", 3000))

                # 公共交通耗时乘 1.3 考虑地铁停靠与等车
                mult = 1.3 if mode == TransportMode.PUBLIC_TRANSIT else 1.0
                duration_min = max(3, int(round((duration_sec * mult) / 60.0)))
                walking_m = (
                    distance_m
                    if mode == TransportMode.WALKING
                    else min(distance_m, max(100, int(distance_m * 0.15)))
                )

                cells.append(
                    RouteMatrixCell(
                        origin_place_id=orig_id,
                        destination_place_id=dest_id,
                        mode=mode,
                        status=RouteMatrixStatus.OK,
                        duration_minutes=duration_min,
                        distance_meters=distance_m,
                        walking_meters=walking_m,
                        cost=Money(amount=400, currency="CNY")
                        if mode == TransportMode.PUBLIC_TRANSIT
                        else None,
                    )
                )

        return cells

    def _fallback_haversine(
        self,
        origins: list[tuple[str, GeoPoint]],
        destinations: list[tuple[str, GeoPoint]],
        mode: TransportMode,
    ) -> list[RouteMatrixCell]:
        speed = 75 if mode == TransportMode.WALKING else 400
        cells = []
        for orig_id, orig_pt in origins:
            for dest_id, dest_pt in destinations:
                dist = haversine_distance_meters(orig_pt, dest_pt)
                minutes = max(3, int(round((dist * 1.3) / speed)))
                cells.append(
                    RouteMatrixCell(
                        origin_place_id=orig_id,
                        destination_place_id=dest_id,
                        mode=mode,
                        status=RouteMatrixStatus.OK,
                        duration_minutes=minutes,
                        distance_meters=dist,
                        walking_meters=dist if mode == TransportMode.WALKING else min(dist, 500),
                    )
                )
        return cells
