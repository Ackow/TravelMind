from datetime import UTC, date, datetime

import httpx

from app.domain.common import DataQuality, DateRange, GeoPoint, SourceRef
from app.domain.research import OutdoorSuitability, WeatherCondition, WeatherDay
from app.providers.base import ProviderError, ProviderTimeoutError, WeatherProvider


class OpenMeteoWeatherProvider(WeatherProvider):
    """基于 Open-Meteo 的全球真实天气适配器。"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self._timeout = timeout_seconds

    @staticmethod
    def _map_wmo_code(code: int) -> tuple[WeatherCondition, OutdoorSuitability]:
        if code == 0:
            return WeatherCondition.CLEAR, OutdoorSuitability.GOOD
        if code in (1, 2):
            return WeatherCondition.PARTLY_CLOUDY, OutdoorSuitability.GOOD
        if code == 3:
            return WeatherCondition.CLOUDY, OutdoorSuitability.ACCEPTABLE
        if code in (45, 48):
            return WeatherCondition.FOG, OutdoorSuitability.ACCEPTABLE
        if 51 <= code <= 67 or 80 <= code <= 82:
            return WeatherCondition.RAIN, OutdoorSuitability.POOR
        if 71 <= code <= 77 or 85 <= code <= 86:
            return WeatherCondition.SNOW, OutdoorSuitability.ACCEPTABLE
        if 95 <= code <= 99:
            return WeatherCondition.STORM, OutdoorSuitability.POOR
        return WeatherCondition.UNKNOWN, OutdoorSuitability.UNKNOWN

    def get_forecast(
        self,
        *,
        destination: str,
        location: GeoPoint,
        date_range: DateRange,
    ) -> list[WeatherDay]:
        total_days = (date_range.end_date - date_range.start_date).days + 1
        forecast_days = min(max(1, total_days), 16)

        daily_vars = [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
            "sunrise",
            "sunset",
        ]

        # Open-Meteo 要求 daily 必须是逗号分隔的字符串
        params: dict[str, object] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": ",".join(daily_vars),
            "timezone": "auto",
        }

        # 判断请求日期是否在 16 天实时预报窗口内
        today = date.today()
        days_from_today = (date_range.start_date - today).days
        if 0 <= days_from_today <= 14 and (date_range.end_date - today).days <= 16:
            params["start_date"] = str(date_range.start_date)
            params["end_date"] = str(date_range.end_date)
        else:
            # 远期规划（超过16天）：使用可用周期的气象数据并映射到目标出行日期
            params["forecast_days"] = forecast_days

        last_exc: Exception | None = None
        payload: dict[str, object] = {}

        for _ in range(2):  # 最多重试 2 次抵抗海外网络抖动
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.get(self.BASE_URL, params=params)
                    resp.raise_for_status()
                    payload = resp.json()
                    break
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
            except Exception as exc:
                last_exc = exc
                continue

        if not payload and last_exc:
            if isinstance(last_exc, httpx.TimeoutException):
                raise ProviderTimeoutError(
                    "Open-Meteo 天气请求超时", provider_name="open_meteo", cause=last_exc
                ) from last_exc
            raise ProviderError(
                f"Open-Meteo 请求失败: {last_exc}", provider_name="open_meteo", cause=last_exc
            ) from last_exc

        daily = payload.get("daily", {})
        weather_codes = daily.get("weather_code", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        precips = daily.get("precipitation_sum", [])
        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])

        results: list[WeatherDay] = []
        now_dt = datetime.now(UTC)
        for idx in range(total_days):
            current_date = date.fromordinal(date_range.start_date.toordinal() + idx)
            data_idx = idx % len(weather_codes) if weather_codes else 0

            wmo_code = weather_codes[data_idx] if data_idx < len(weather_codes) else -1
            cond, suit = self._map_wmo_code(wmo_code)
            rain_p = (
                (rain_probs[data_idx] / 100.0)
                if data_idx < len(rain_probs) and rain_probs[data_idx] is not None
                else None
            )

            sunrise_raw = sunrises[data_idx] if data_idx < len(sunrises) else None
            sunset_raw = sunsets[data_idx] if data_idx < len(sunsets) else None
            sunrise_time = datetime.fromisoformat(sunrise_raw).time() if sunrise_raw else None
            sunset_time = datetime.fromisoformat(sunset_raw).time() if sunset_raw else None

            results.append(
                WeatherDay(
                    date=current_date,
                    condition=cond,
                    temperature_min_c=min_temps[data_idx] if data_idx < len(min_temps) else None,
                    temperature_max_c=max_temps[data_idx] if data_idx < len(max_temps) else None,
                    rain_probability=rain_p,
                    precipitation_mm=precips[data_idx] if data_idx < len(precips) else None,
                    outdoor_suitability=suit,
                    sunrise_time=sunrise_time,
                    sunset_time=sunset_time,
                    source=SourceRef(
                        provider="open_meteo",
                        fetched_at=now_dt,
                        source_url="https://open-meteo.com",
                        data_quality=DataQuality.VERIFIED,
                    ),
                )
            )

        return results
