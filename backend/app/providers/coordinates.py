import math

from app.domain.common import GeoPoint


class CoordinateConverter:
    """WGS-84 (国际标准 GPS) 与 GCJ-02 (中国火星坐标系) 双向纠偏转换工具。"""

    A = 6378245.0  # 克拉索夫斯基椭球长半轴
    EE = 0.00669342162296594323  # 椭球偏心率平方

    @classmethod
    def is_out_of_china(cls, lat: float, lon: float) -> bool:
        """判断坐标是否在中国大陆境外（境外无需纠偏）。"""
        return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)

    @classmethod
    def _transform_lat(cls, x: float, y: float) -> float:
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (
            (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        )
        return ret

    @classmethod
    def _transform_lon(cls, x: float, y: float) -> float:
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (
            (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi))
            * 2.0
            / 3.0
        )
        return ret

    @classmethod
    def wgs84_to_gcj02(cls, pt: GeoPoint) -> GeoPoint:
        """国际 GPS 坐标转换为高德 GCJ-02 坐标。"""
        if cls.is_out_of_china(pt.latitude, pt.longitude):
            return pt
        dlat = cls._transform_lat(pt.longitude - 105.0, pt.latitude - 35.0)
        dlon = cls._transform_lon(pt.longitude - 105.0, pt.latitude - 35.0)
        radlat = pt.latitude / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - cls.EE * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((cls.A * (1 - cls.EE)) / (magic * sqrtmagic) * math.pi)
        dlon = (dlon * 180.0) / (cls.A / sqrtmagic * math.cos(radlat) * math.pi)
        return GeoPoint(
            latitude=round(pt.latitude + dlat, 6), longitude=round(pt.longitude + dlon, 6)
        )

    @classmethod
    def gcj02_to_wgs84(cls, pt: GeoPoint) -> GeoPoint:
        """高德 GCJ-02 坐标逆向转换还原为 WGS-84 领域模型标准坐标。"""
        if cls.is_out_of_china(pt.latitude, pt.longitude):
            return pt
        dlat = cls._transform_lat(pt.longitude - 105.0, pt.latitude - 35.0)
        dlon = cls._transform_lon(pt.longitude - 105.0, pt.latitude - 35.0)
        radlat = pt.latitude / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - cls.EE * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((cls.A * (1 - cls.EE)) / (magic * sqrtmagic) * math.pi)
        dlon = (dlon * 180.0) / (cls.A / sqrtmagic * math.cos(radlat) * math.pi)
        return GeoPoint(
            latitude=round(pt.latitude - dlat, 6), longitude=round(pt.longitude - dlon, 6)
        )
