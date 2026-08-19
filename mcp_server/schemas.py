from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, Field


class WeatherToolInput(BaseModel):
    """查询指定目的地在指定日期范围内的真实天气预报"""
    destination: str = Field(description="目标目的地城市名称，例如 'Tokyo' 或 '南京'")
    start_date: date = Field(description="行程开始自然日期，格式 YYYY-MM-DD")
    end_date: date = Field(description="行程结束自然日期，格式 YYYY-MM-DD")


class PoiSearchInput(BaseModel):
    """根据分类、关键词或辐射半径检索目的地的景点/美食/场馆点位"""
    destination: str = Field(description="目标城市，例如 'Tokyo'")
    query: str | None = Field(default=None, description="搜索关键词，例如 '浅草寺' 或 '拉面'")
    category: Literal["attraction", "restaurant", "cafe", "culture", "shopping", "all"] = Field(
        default="all",
        description="POI 分类类型",
    )
    center_lat: float | None = Field(default=None, description="中心点纬度（用于周边搜索）")
    center_lng: float | None = Field(default=None, description="中心点经度（用于周边搜索）")
    radius_meters: int = Field(default=10000, ge=500, le=50000, description="搜索半径（米）")
    limit: int = Field(default=20, ge=1, le=50, description="最大返回数量")


class RouteToolInput(BaseModel):
    """计算两点之间在指定交通方式下的真实通勤距离、耗时与预估费用"""
    origin_lat: float = Field(description="起点纬度")
    origin_lng: float = Field(description="起点经度")
    destination_lat: float = Field(description="终点纬度")
    destination_lng: float = Field(description="终点经度")
    transport_mode: Literal["walking", "transit", "driving", "cycling"] = Field(
        default="transit",
        description="交通出行方式",
    )


class ToolResponse(BaseModel):
    """统一工具响应外壳"""
    success: bool = Field(description="工具执行是否成功")
    data: Any = Field(default=None, description="成功返回的业务负载数据")
    error: str | None = Field(default=None, description="错误详情说明")
    provider_source: str = Field(description="实际响应的底层 Provider 标识")
