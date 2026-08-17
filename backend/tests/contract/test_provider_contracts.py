from datetime import date
import pytest
from app.domain.common import DateRange, GeoPoint
from app.domain.research import Place, RouteMatrixCell, RouteMatrixStatus, WeatherDay
from app.domain.trip import TransportMode
from app.providers.poi.overpass import OverpassPoiProvider
from app.providers.route.osrm import OSRMRouteProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider


@pytest.mark.parametrize("provider_cls", [OpenMeteoWeatherProvider])
def test_weather_provider_satisfies_contract(provider_cls: type) -> None:
    """验证南京 8.20 - 8.23 真实天气接口返回与契约合规性。"""
    provider = provider_cls()
    # 南京市中心坐标 (纬度 32.0603, 经度 118.7969)
    nanjing = GeoPoint(latitude=32.0603, longitude=118.7969)
    dates = DateRange(start_date=date(2026, 8, 20), end_date=date(2026, 8, 23))

    results = provider.get_forecast(destination="Nanjing", location=nanjing, date_range=dates)

    assert len(results) == dates.day_count
    print(f"\n🌤️ 【Open-Meteo 南京真实天气返回（8.20 - 8.23 共 {len(results)} 天）】:")
    for w in results:
        assert isinstance(w, WeatherDay)
        assert w.condition is not None
        assert w.outdoor_suitability is not None
        assert w.source.provider != ""
        print(
            f"  📅 {w.date} | 状况: {w.condition.value:<10} | "
            f"气温: {w.temperature_min_c}°C ~ {w.temperature_max_c}°C | "
            f"降雨概率: {f'{w.rain_probability:.0%}' if w.rain_probability is not None else '未知'} | "
            f"日出: {w.sunrise_time} | 日落: {w.sunset_time} | 适宜度: {w.outdoor_suitability.value}"
        )


@pytest.mark.parametrize("provider_cls", [OverpassPoiProvider])
def test_poi_provider_satisfies_contract(provider_cls: type) -> None:
    """验证南京真实景点 POI 检索与 Place 领域模型契约。"""
    provider = provider_cls()
    nanjing_center = GeoPoint(latitude=32.0603, longitude=118.7969)

    places = provider.search_places(
        destination="Nanjing",
        location=nanjing_center,
        limit=8,
    )

    assert len(places) > 0
    print(f"\n📍 【OpenStreetMap 南京真实地点检索返回（共 {len(places)} 个）】:")
    for p in places:
        assert isinstance(p, Place)
        assert p.id != ""
        assert p.name != ""
        assert len(p.categories) > 0
        assert p.location.latitude != 0
        assert len(p.opening_periods) > 0
        print(
            f"  🏛️ [{p.id}] {p.name:<24} | 分类: {','.join(c.value for c in p.categories):<12} | "
            f"属性: {p.indoor_outdoor.value:<7} | 预估: {p.estimated_visit_minutes}分 | 坐标: ({p.location.latitude:.4f}, {p.location.longitude:.4f})"
        )


@pytest.mark.parametrize("provider_cls", [OSRMRouteProvider])
def test_route_provider_satisfies_contract(provider_cls: type) -> None:
    """验证南京核心交通枢纽与景点之间的真实路线矩阵与耗时。"""
    provider = provider_cls()
    origins = [
        ("nanjing_south_station", GeoPoint(latitude=31.9696, longitude=118.7972)),  # 南京南站
        ("xinjiekou", GeoPoint(latitude=32.0438, longitude=118.7842)),              # 新街口
    ]
    destinations = [
        ("sun_yat_sen_mausoleum", GeoPoint(latitude=32.0622, longitude=118.8488)),  # 中山陵
        ("confucius_temple", GeoPoint(latitude=32.0194, longitude=118.7885)),       # 夫子庙
    ]

    cells = provider.get_route_matrix(
        origins=origins,
        destinations=destinations,
        mode=TransportMode.PUBLIC_TRANSIT,
    )

    assert len(cells) == len(origins) * len(destinations)
    print(f"\n🚗 【OSRM 南京真实路线与交通耗时矩阵返回（共 {len(cells)} 条路径）】:")
    for c in cells:
        assert isinstance(c, RouteMatrixCell)
        assert c.status == RouteMatrixStatus.OK
        assert c.duration_minutes is not None and c.duration_minutes > 0
        dist_str = f"{c.distance_meters}m" if c.distance_meters else "估算"
        print(
            f"  🧭 {c.origin_place_id:<22} ──({c.mode.value})──> {c.destination_place_id:<22} | "
            f"耗时: {c.duration_minutes:>2} 分钟 | 距离: {dist_str}"
        )