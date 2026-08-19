from mcp_server.server import get_route, get_weather, search_poi


def test_mcp_tools_direct_execution():
    """验证：MCP Server 注册的各项工具函数能够正确执行并输出标准字典结构。"""
    # 1. 测试天气工具
    weather_res = get_weather("南京", "2026-10-01", "2026-10-03")
    assert weather_res["success"] is True
    assert len(weather_res["data"]) >= 3

    # 2. 测试 POI 工具
    poi_res = search_poi("南京", "夫子庙", category="attraction", limit=5)
    assert poi_res["success"] is True
    assert len(poi_res["data"]) > 0

    # 3. 测试路线工具
    route_res = get_route(32.0195, 118.7876, 32.0416, 118.7842, mode="transit")
    assert route_res["success"] is True
    assert "distance_meters" in route_res["data"]
    assert "duration_minutes" in route_res["data"]
