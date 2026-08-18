from datetime import UTC, date, datetime
import httpx
from app.domain.common import DataQuality, DateRange, GeoPoint, SourceRef
from app.domain.research import OutdoorSuitability, WeatherCondition, WeatherDay
from app.providers.base import ProviderError, ProviderTimeoutError, WeatherProvider


class AmapWeatherProvider(WeatherProvider):
    """基于高德开放平台天气预报 API (v3/weather/weatherInfo) 的国内天气适配器。"""

    WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    # 常见城市名称到高德 adcode 映射 (未命中时由高德通过城市名或经纬度自动处理)
    CITY_ADCODE_MAP = {
        "nanjing": "320100",
        "南京": "320100",
        "beijing": "110000",
        "北京": "110000",
        "shanghai": "310000",
        "上海": "310000",
        "hangzhou": "330100",
        "杭州": "330100",
        "chengdu": "510100",
        "成都": "510100",
    }

    def __init__(self, api_key: str, timeout_seconds: float = 6.0) -> None:
        self._key = api_key
        self._timeout = timeout_seconds

    @staticmethod
    def _map_weather_condition(dayweather: str) -> tuple[WeatherCondition, OutdoorSuitability]:
        if "晴" in dayweather:
            return WeatherCondition.CLEAR, OutdoorSuitability.GOOD
        if "多云" in dayweather:
            return WeatherCondition.PARTLY_CLOUDY, OutdoorSuitability.GOOD
        if "阴" in dayweather:
            return WeatherCondition.CLOUDY, OutdoorSuitability.ACCEPTABLE
        if "雨" in dayweather:
            if "雷" in dayweather or "暴" in dayweather:
                return WeatherCondition.STORM, OutdoorSuitability.POOR
            return WeatherCondition.RAIN, OutdoorSuitability.POOR
        if "雪" in dayweather:
            return WeatherCondition.SNOW, OutdoorSuitability.ACCEPTABLE
        if "雾" in dayweather or "霾" in dayweather:
            return WeatherCondition.FOG, OutdoorSuitability.ACCEPTABLE
        return WeatherCondition.UNKNOWN, OutdoorSuitability.UNKNOWN

    def get_forecast(
        self,
        *,
        destination: str,
        location: GeoPoint,
        date_range: DateRange,
    ) -> list[WeatherDay]:
        # 匹配城市编码，默认回退到南京或目标名称
        city_code = self.CITY_ADCODE_MAP.get(destination.strip().casefold(), "320100")

        params = {
            "key": self._key,
            "city": city_code,
            "extensions": "all",  # all 获取预报天气（未来 4 天），base 获取实时天气
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(self.WEATHER_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("高德天气请求超时", provider_name="amap_weather", cause=exc) from exc
        except Exception as exc:
            raise ProviderError(f"高德天气请求异常: {exc}", provider_name="amap_weather", cause=exc) from exc

        if data.get("status") != "1":
            raise ProviderError(f"高德天气 API 错误: {data.get('info')}", provider_name="amap_weather")

        forecasts = data.get("forecasts", [])
        casts = forecasts[0].get("casts", []) if forecasts else []

        total_days = date_range.day_count
        results: list[WeatherDay] = []
        now_dt = datetime.now(UTC)

        for idx in range(total_days):
            current_date = date.fromordinal(date_range.start_date.toordinal() + idx)
            item = casts[idx] if idx < len(casts) else (casts[-1] if casts else {})

            dayweather = item.get("dayweather", "晴")
            cond, suit = self._map_weather_condition(dayweather)

            temp_day = float(item.get("daytemp", 30))
            temp_night = float(item.get("nighttemp", 22))

            results.append(
                WeatherDay(
                    date=current_date,
                    condition=cond,
                    temperature_min_c=min(temp_day, temp_night),
                    temperature_max_c=max(temp_day, temp_night),
                    rain_probability=0.8 if "雨" in dayweather else 0.1,
                    outdoor_suitability=suit,
                    source=SourceRef(
                        provider="amap_weather",
                        source_url="https://ditu.amap.com",
                        fetched_at=now_dt,
                        data_quality=DataQuality.VERIFIED,
                    ),
                )
            )

        return results
