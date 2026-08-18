from datetime import date
import os
import pytest
from app.core.config import get_settings
from app.domain.common import DateRange, GeoPoint
from app.domain.research import Place, RouteMatrixCell, RouteMatrixStatus, WeatherDay
from app.domain.trip import TransportMode
from app.infrastructure.composite_facts_factory import CompositeFactsFactory
from app.providers.base import ProviderError
from app.providers.poi.amap import AmapPoiProvider
from app.providers.poi.overpass import OverpassPoiProvider
from app.providers.route.amap import AmapRouteProvider
from app.providers.route.osrm import OSRMRouteProvider
from app.providers.weather.amap import AmapWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.weather.qweather import QWeatherProvider


# ==========================================
# 1. 全球开源数据源契约测试 (免 Key)
# ==========================================

def test_open_meteo_weather_satisfies_contract() -> None:
    """验证 Open-Meteo 全球天气适配器输出符合领域模型契约。"""
    provider = OpenMeteoWeatherProvider()
    nanjing = GeoPoint(latitude=32.0603, longitude=118.7969)
    dates = DateRange(start_date=date(2026, 8, 20), end_date=date(2026, 8, 23))

    results = provider.get_forecast(destination="Nanjing", location=nanjing, date_range=dates)

    assert len(results) == dates.day_count
    print(f"\n[Open-Meteo] 全球开源天气返回（共 {len(results)} 天）:")
    for w in results:
        assert isinstance(w, WeatherDay)
        assert w.condition is not None
        assert w.outdoor_suitability is not None
        assert w.source.provider == "open_meteo"
        print(
            f"  日期: {w.date} | 状况: {w.condition.value:<10} | "
            f"气温: {w.temperature_min_c}°C ~ {w.temperature_max_c}°C | "
            f"降雨概率: {f'{w.rain_probability:.0%}' if w.rain_probability is not None else '未知'} | "
            f"日落: {w.sunset_time} | 适宜度: {w.outdoor_suitability.value}"
        )


def test_overpass_poi_satisfies_contract() -> None:
    """验证 OpenStreetMap Overpass 全球 POI 检索适配器契约。"""
    provider = OverpassPoiProvider()
    nanjing_center = GeoPoint(latitude=32.0603, longitude=118.7969)

    try:
        places = provider.search_places(
            destination="Nanjing",
            location=nanjing_center,
            limit=8,
        )
    except ProviderError as exc:
        if "超时" in str(exc) or "timeout" in str(exc).lower():
            pytest.skip(f"海外 OpenStreetMap Overpass 节点网络超时，跳过本次测试: {exc}")
        raise

    assert len(places) > 0
    print(f"\n[OSM Overpass] 全球地点检索返回（共 {len(places)} 个）:")
    for p in places:
        assert isinstance(p, Place)
        assert p.id != ""
        assert p.name != ""
        assert len(p.categories) > 0
        assert p.location.latitude != 0
        print(
            f"  [{p.id}] {p.name:<24} | 分类: {','.join(c.value for c in p.categories):<12} | "
            f"属性: {p.indoor_outdoor.value:<7} | 坐标: ({p.location.latitude:.4f}, {p.location.longitude:.4f})"
        )


def test_osrm_route_satisfies_contract() -> None:
    """验证 OSRM 开源路线与耗时矩阵适配器契约。"""
    provider = OSRMRouteProvider()
    origins = [
        ("nanjing_south_station", GeoPoint(latitude=31.9696, longitude=118.7972)),
        ("xinjiekou", GeoPoint(latitude=32.0438, longitude=118.7842)),
    ]
    destinations = [
        ("sun_yat_sen_mausoleum", GeoPoint(latitude=32.0622, longitude=118.8488)),
        ("confucius_temple", GeoPoint(latitude=32.0194, longitude=118.7885)),
    ]

    cells = provider.get_route_matrix(
        origins=origins,
        destinations=destinations,
        mode=TransportMode.PUBLIC_TRANSIT,
    )

    assert len(cells) == len(origins) * len(destinations)
    print(f"\n[OSRM] 开源路线耗时矩阵返回（共 {len(cells)} 条路径）:")
    for c in cells:
        assert isinstance(c, RouteMatrixCell)
        assert c.status == RouteMatrixStatus.OK
        assert c.duration_minutes is not None and c.duration_minutes > 0
        dist_str = f"{c.distance_meters}m" if c.distance_meters else "估算"
        print(
            f"  {c.origin_place_id:<22} --({c.mode.value})--> {c.destination_place_id:<22} | "
            f"耗时: {c.duration_minutes:>2} 分钟 | 距离: {dist_str} | 步行: {c.walking_meters}m"
        )


# ==========================================
# 2. 国内高精度商业数据源契约测试 (高德 AMap)
# ==========================================

def test_amap_poi_and_route_satisfies_contract() -> None:
    """验证高德地图国内高精度 POI 检索与路线矩阵契约 (配置 AMAP_API_KEY 时执行)。"""
    settings = get_settings()
    api_key = settings.AMAP_API_KEY or os.getenv("AMAP_API_KEY")

    if not api_key:
        pytest.skip("未在 .env 中配置 AMAP_API_KEY，跳过高德接口测试")

    # 1. 测试高德 POI 周边搜索
    poi_provider = AmapPoiProvider(api_key=api_key)
    nanjing_center = GeoPoint(latitude=32.0603, longitude=118.7969)
    places = poi_provider.search_places(destination="Nanjing", location=nanjing_center, limit=8)

    assert len(places) > 0
    print(f"\n[高德 AMap] 国内高精度地点检索返回（共 {len(places)} 个）:")
    for p in places:
        assert isinstance(p, Place)
        assert p.id.startswith("amap_")
        print(
            f"  [{p.id}] {p.name:<24} | 分类: {','.join(c.value for c in p.categories):<12} | "
            f"评分: {p.rating}分 | 坐标: ({p.location.latitude:.4f}, {p.location.longitude:.4f})"
        )

    # 2. 测试高德真实路线矩阵
    route_provider = AmapRouteProvider(api_key=api_key)
    origins = [("nanjing_south_station", GeoPoint(latitude=31.9696, longitude=118.7972))]
    destinations = [("sun_yat_sen_mausoleum", GeoPoint(latitude=32.0622, longitude=118.8488))]
    cells = route_provider.get_route_matrix(origins=origins, destinations=destinations, mode=TransportMode.PUBLIC_TRANSIT)

    assert len(cells) == 1
    c = cells[0]
    assert c.status == RouteMatrixStatus.OK
    cost_str = f"{c.cost.amount/100:.1f}元" if c.cost else "免费"
    print(f"  [高德路线] {c.origin_place_id} -> {c.destination_place_id} | 耗时: {c.duration_minutes}分钟 | 距离: {c.distance_meters}米 | 预估花费: {cost_str}")


def test_amap_weather_satisfies_contract() -> None:
    """验证高德地图国内 4 天高精度天气预报契约 (配置 AMAP_API_KEY 时执行)。"""
    settings = get_settings()
    api_key = settings.AMAP_API_KEY or os.getenv("AMAP_API_KEY")

    if not api_key:
        pytest.skip("未在 .env 中配置 AMAP_API_KEY，跳过高德天气测试")

    provider = AmapWeatherProvider(api_key=api_key)
    nanjing = GeoPoint(latitude=32.0603, longitude=118.7969)
    dates = DateRange(start_date=date(2026, 8, 20), end_date=date(2026, 8, 23))

    results = provider.get_forecast(destination="Nanjing", location=nanjing, date_range=dates)
    assert len(results) == dates.day_count
    print(f"\n[高德 AMap] 国内真实天气预报返回（共 {len(results)} 天）:")
    for w in results:
        assert isinstance(w, WeatherDay)
        print(f"  日期: {w.date} | 状况: {w.condition.value:<10} | 气温: {w.temperature_min_c}~{w.temperature_max_c}C | 适宜度: {w.outdoor_suitability.value}")


def test_qweather_satisfies_contract() -> None:
    """验证和风天气国内预报契约 (配置 QWEATHER_API_KEY 时执行，支持专属 QWEATHER_HOST)。"""
    settings = get_settings()
    api_key = settings.QWEATHER_API_KEY or os.getenv("QWEATHER_API_KEY")

    if not api_key:
        pytest.skip("未在 .env 中配置 QWEATHER_API_KEY，跳过和风天气测试")

    provider = QWeatherProvider(api_key=api_key, api_host=settings.QWEATHER_HOST)
    nanjing = GeoPoint(latitude=32.0603, longitude=118.7969)
    dates = DateRange(start_date=date(2026, 8, 20), end_date=date(2026, 8, 23))

    try:
        results = provider.get_forecast(destination="Nanjing", location=nanjing, date_range=dates)
        assert len(results) == dates.day_count
        print(f"\n[和风 QWeather] 国内精准天气返回（共 {len(results)} 天）:")
        for w in results:
            assert isinstance(w, WeatherDay)
            print(f"  日期: {w.date} | 状况: {w.condition.value:<10} | 气温: {w.temperature_min_c}~{w.temperature_max_c}C")
    except ProviderError as exc:
        if "invalid-host" in str(exc).lower():
            pytest.skip(f"和风天气提示 invalid-host（需要在控制台查看项目的专属 API Host 并在 .env 中配置 QWEATHER_HOST）: {exc}")
        raise


# ==========================================
# 3. 智能双模路由器 (CompositeFactsFactory) 路由测试
# ==========================================

def test_composite_facts_factory_dual_mode_routing() -> None:
    """验证事实工厂的国内/海外地理围栏自动分流能力。"""
    settings = get_settings()
    factory = CompositeFactsFactory(
        amap_key=settings.AMAP_API_KEY,
        qweather_key=settings.QWEATHER_API_KEY,
    )

    # 1. 海外城市 (东京坐标 35.6762, 139.6503 位于中国大陆境外)
    tokyo = GeoPoint(latitude=35.6762, longitude=139.6503)
    weather_p, poi_p, route_p = factory._resolve_providers(tokyo)
    assert isinstance(weather_p, OpenMeteoWeatherProvider)
    assert isinstance(poi_p, OverpassPoiProvider)
    assert isinstance(route_p, OSRMRouteProvider)

    # 2. 国内城市 (南京坐标 32.0603, 118.7969 位于中国大陆境内)
    nanjing = GeoPoint(latitude=32.0603, longitude=118.7969)
    weather_p, poi_p, route_p = factory._resolve_providers(nanjing)
    if settings.AMAP_API_KEY:
        assert isinstance(poi_p, AmapPoiProvider)
        assert isinstance(route_p, AmapRouteProvider)
    else:
        # 无 Key 时自动安全降级到全球开源适配器
        assert isinstance(poi_p, OverpassPoiProvider)