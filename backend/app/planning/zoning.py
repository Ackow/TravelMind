from math import asin, cos, radians, sin, sqrt

from app.domain.research import Place, RouteMatrix, RouteMatrixStatus
from app.planning.models import Zone


def haversine_km(first: Place, second: Place) -> float:
    """计算两个经纬度之间的球面距离。"""
    earth_radius_km = 6371.0088
    lat1 = radians(first.location.latitude)
    lon1 = radians(first.location.longitude)
    lat2 = radians(second.location.latitude)
    lon2 = radians(second.location.longitude)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


def cluster_distance(
    first: tuple[str, ...],
    second: tuple[str, ...],
    places_by_id: dict[str, Place],
) -> float:
    """使用两个簇之间最近的地点距离，适合小规模单城市 MVP。"""
    return min(
        haversine_km(places_by_id[left], places_by_id[right]) for left in first for right in second
    )


def clusters_have_route(
    first: tuple[str, ...],
    second: tuple[str, ...],
    route_matrix: RouteMatrix,
) -> bool:
    """判断两个簇之间是否至少存在一个方向的可用路线事实。"""
    left = set(first)
    right = set(second)
    return any(
        cell.status == RouteMatrixStatus.OK
        and (
            (cell.origin_place_id in left and cell.destination_place_id in right)
            or (cell.origin_place_id in right and cell.destination_place_id in left)
        )
        for cell in route_matrix.cells
    )


def build_zones(
    *,
    places: tuple[Place, ...],
    route_matrix: RouteMatrix,
    target_zone_count: int,
) -> tuple[Zone, ...]:
    """使用确定性凝聚聚类，把候选地点合并到目标区域数量。

    优先合并存在路线事实的簇，再比较地理距离，最后用 ID 作为稳定兜底。
    这不是全局最优聚类，但对于 10～20 个单城市 POI 足够直观。
    """
    if target_zone_count < 1:
        raise ValueError("target_zone_count must be positive")
    if not places:
        return ()

    places_by_id = {place.id: place for place in places}
    clusters = [(place.id,) for place in sorted(places, key=lambda item: item.id)]
    expected_count = min(target_zone_count, len(clusters))

    while len(clusters) > expected_count:
        choices = []
        for left_index, left in enumerate(clusters):
            for right_index in range(left_index + 1, len(clusters)):
                right = clusters[right_index]
                route_missing = not clusters_have_route(
                    left,
                    right,
                    route_matrix,
                )
                choices.append(
                    (
                        route_missing,
                        cluster_distance(left, right, places_by_id),
                        left,
                        right,
                        left_index,
                        right_index,
                    )
                )

        _, _, left, right, left_index, right_index = min(choices)
        merged = tuple(sorted((*left, *right)))
        clusters = [
            cluster
            for index, cluster in enumerate(clusters)
            if index not in {left_index, right_index}
        ]
        clusters.append(merged)
        clusters.sort()

    return tuple(
        Zone(id=f"zone-{index:02d}", place_ids=cluster)
        for index, cluster in enumerate(sorted(clusters), start=1)
    )
