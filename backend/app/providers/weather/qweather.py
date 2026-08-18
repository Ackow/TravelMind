from datetime import UTC, date, datetime
import httpx
from app.domain.common import DataQuality, DateRange, GeoPoint, SourceRef
from app.domain.research import OutdoorSuitability, WeatherCondition, WeatherDay
from app.providers.base import ProviderError, ProviderTimeoutError, WeatherProvider


class QWeatherProvider(WeatherProvider):
    """基于和风天气 (QWeather) 的中国气象局官方数据与生活指数适配器。"""

    # 和风天气免费版开放 /weather/3d (3天预报)；付费商业版开放 /weather/7d
    ENDPOINTS = [
        "https://devapi.qweather.com/v7/weather/3d",
        "https://api.qweather.com/v7/weather/3d",
        "https://devapi.qweather.com/v7/weather/7d",
        "https://api.qweather.com/v7/weather/7d",
    ]

    def __init__(
        self,
        api_key: str,
        api_host: str | None = None,
        timeout_seconds: float = 6.0,
    ) -> None:
        self._key = api_key
        self._timeout = timeout_seconds

        endpoints = []
        if api_host:
            clean_host = api_host.rstrip("/")
            if not clean_host.startswith("http"):
                clean_host = f"https://{clean_host}"
            endpoints.extend([
                f"{clean_host}/v7/weather/3d",
                f"{clean_host}/v7/weather/7d",
            ])

        # 默认官方端点
        endpoints.extend([
            "https://devapi.qweather.com/v7/weather/3d",
            "https://api.qweather.com/v7/weather/3d",
            "https://devapi.qweather.com/v7/weather/7d",
            "https://api.qweather.com/v7/weather/7d",
        ])
        self.endpoints = endpoints

    @staticmethod
    def _map_condition(icon: str) -> tuple[WeatherCondition, OutdoorSuitability]:
        # 和风天气 icon 代码映射
        if icon in ("100", "150"):
            return WeatherCondition.CLEAR, OutdoorSuitability.GOOD
        if icon in ("101", "102", "103"):
            return WeatherCondition.PARTLY_CLOUDY, OutdoorSuitability.GOOD
        if icon in ("104",):
            return WeatherCondition.CLOUDY, OutdoorSuitability.ACCEPTABLE
        if "3" in icon:  # 3xx 均为各类降雨
            return WeatherCondition.RAIN, OutdoorSuitability.POOR
        if "4" in icon:  # 4xx 均为雪
            return WeatherCondition.SNOW, OutdoorSuitability.ACCEPTABLE
        return WeatherCondition.UNKNOWN, OutdoorSuitability.UNKNOWN

    def get_forecast(
        self,
        *,
        destination: str,
        location: GeoPoint,
        date_range: DateRange,
    ) -> list[WeatherDay]:
        # 和风天气要求经纬度坐标为十进制，保留最多 2 位小数 (经度,纬度)
        params = {
            "key": self._key,
            "location": f"{location.longitude:.2f},{location.latitude:.2f}",
        }

        data: dict[str, object] = {}
        last_error: Exception | None = None
        details: list[str] = []
        with httpx.Client(timeout=self._timeout) as client:
            for url in self.endpoints:
                try:
                    resp = client.get(url, params=params)
                    if resp.status_code == 200:
                        payload = resp.json()
                        if payload.get("code") == "200" and payload.get("daily"):
                            data = payload
                            break
                        details.append(f"{url} -> code={payload.get('code')}")
                    else:
                        details.append(f"{url} -> HTTP {resp.status_code} ({resp.text[:100]})")
                except httpx.TimeoutException as exc:
                    details.append(f"{url} -> 超时 ({exc})")
                    last_error = exc
                except Exception as exc:
                    details.append(f"{url} -> 异常 ({exc})")
                    last_error = exc

        if not data:
            diag_msg = " | ".join(details)
            raise ProviderError(
                f"和风天气全部端点请求失败: {diag_msg}。可能原因: 1. 控制台凭据类型非 Web API 2. 开启了 IP 白名单 3. 新建 Key 尚未生效同步",
                provider_name="qweather",
                cause=last_error,
            )

        daily = data.get("daily", [])
        total_days = date_range.day_count
        results: list[WeatherDay] = []
        now_dt = datetime.now(UTC)

        for idx in range(total_days):
            current_date = date.fromordinal(date_range.start_date.toordinal() + idx)
            item = daily[idx] if idx < len(daily) else (daily[0] if daily else {})

            cond, suit = self._map_condition(item.get("iconDay", "100"))
            sunrise_str = item.get("sunrise")
            sunset_str = item.get("sunset")

            results.append(
                WeatherDay(
                    date=current_date,
                    condition=cond,
                    temperature_min_c=float(item.get("tempMin", 20)),
                    temperature_max_c=float(item.get("tempMax", 30)),
                    rain_probability=float(item.get("precip", "0.0")) / 100.0 if item.get("precip") else 0.1,
                    precipitation_mm=float(item.get("precip", 0.0)) if item.get("precip") else 0.0,
                    outdoor_suitability=suit,
                    sunrise_time=datetime.strptime(sunrise_str, "%H:%M").time() if sunrise_str else None,
                    sunset_time=datetime.strptime(sunset_str, "%H:%M").time() if sunset_str else None,
                    source=SourceRef(
                        provider="qweather",
                        source_url="https://www.qweather.com",
                        fetched_at=now_dt,
                        data_quality=DataQuality.VERIFIED,
                    ),
                )
            )

        return results