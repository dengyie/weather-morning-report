"""wttr.in JSON provider and documented wttr.is fallback."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from weather_morning_report.models import (
    CurrentConditions,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherCondition,
    WeatherSnapshot,
)
from weather_morning_report.providers.base import ProviderError

JsonObject = dict[str, Any]


class WttrProvider:
    def __init__(
        self,
        location_name: str,
        location_query: str,
        timezone: ZoneInfo,
        hosts: tuple[str, ...] = ("wttr.in", "wttr.is"),
        timeout_seconds: float = 15,
    ) -> None:
        self.location_name = location_name
        self.location_query = location_query
        self.timezone = timezone
        self.hosts = hosts
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> WeatherSnapshot:
        errors: list[str] = []
        for host in self.hosts:
            try:
                payload = self._request(host)
                return parse_wttr_payload(
                    payload,
                    location_name=self.location_name,
                    timezone=self.timezone,
                    source=host,
                )
            except (ProviderError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{host}: {exc}")
        raise ProviderError("all wttr providers failed: " + "; ".join(errors))

    def _request(self, host: str) -> JsonObject:
        query = quote(self.location_query, safe=",")
        request = Request(
            f"https://{host}/{query}?format=j1",
            headers={"User-Agent": "weather-morning-report/0.2"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(str(exc)) from exc


def parse_wttr_payload(
    payload: JsonObject,
    *,
    location_name: str,
    timezone: ZoneInfo,
    source: str,
    fetched_at: datetime | None = None,
) -> WeatherSnapshot:
    fetched_at = fetched_at or datetime.now(timezone)
    current_data = _first(payload, "current_condition")
    weather_data = _today(payload, fetched_at.date())
    forecast_date = date.fromisoformat(weather_data["date"])

    current = CurrentConditions(
        observed_at=fetched_at,
        condition=_condition(current_data),
        description=_description(current_data),
        temperature_c=_float(current_data, "temp_C"),
        feels_like_c=_float(current_data, "FeelsLikeC"),
        humidity_percent=_int(current_data, "humidity"),
        wind_speed_kph=_float(current_data, "windspeedKmph"),
        wind_direction=current_data.get("winddir16Point"),
        uv_index=_float(current_data, "uvIndex"),
    )
    daily = DailyForecast(
        forecast_date=forecast_date,
        minimum_temperature_c=_float(weather_data, "mintempC"),
        maximum_temperature_c=_float(weather_data, "maxtempC"),
        uv_index=_float(weather_data, "uvIndex"),
    )
    hourly = tuple(
        _parse_hour(point, forecast_date, timezone)
        for point in weather_data.get("hourly", [])
    )
    if not hourly:
        raise ProviderError("today's hourly forecast is empty")

    return WeatherSnapshot(
        location=Location(location_name),
        source=source,
        fetched_at=fetched_at,
        current=current,
        daily=daily,
        hourly=hourly,
    )


def _parse_hour(point: JsonObject, forecast_date: date, timezone: ZoneInfo) -> HourlyForecast:
    raw_time = _int(point, "time")
    hour, minute = divmod(raw_time, 100)
    return HourlyForecast(
        forecast_at=datetime.combine(
            forecast_date,
            datetime.min.time(),
            timezone,
        ).replace(hour=hour, minute=minute),
        condition=_condition(point),
        description=_description(point),
        temperature_c=_float(point, "tempC"),
        feels_like_c=_float(point, "FeelsLikeC"),
        precipitation_probability_percent=_int(point, "chanceofrain"),
        precipitation_mm=_float(point, "precipMM"),
        thunder_probability_percent=_int(point, "chanceofthunder"),
        humidity_percent=_int(point, "humidity"),
        wind_speed_kph=_float(point, "windspeedKmph"),
        uv_index=_float(point, "uvIndex"),
    )


def _today(payload: JsonObject, today: date) -> JsonObject:
    weather = payload.get("weather", [])
    for item in weather:
        if item.get("date") == today.isoformat():
            return item
    if weather:
        return weather[0]
    raise ProviderError("daily forecast is empty")


def _first(payload: JsonObject, key: str) -> JsonObject:
    values = payload.get(key, [])
    if not values:
        raise ProviderError(f"{key} is empty")
    return values[0]


def _description(data: JsonObject) -> str:
    descriptions = data.get("weatherDesc", [])
    if not descriptions:
        return "Unknown"
    return str(descriptions[0].get("value", "Unknown")).strip()


def _condition(data: JsonObject) -> WeatherCondition:
    description = _description(data).lower()
    if "thunder" in description:
        return WeatherCondition.THUNDERSTORM
    if "heavy rain" in description or "torrential" in description:
        return WeatherCondition.HEAVY_RAIN
    if "drizzle" in description:
        return WeatherCondition.DRIZZLE
    if "rain" in description or "shower" in description:
        return WeatherCondition.RAIN
    if "sleet" in description:
        return WeatherCondition.SLEET
    if "snow" in description:
        return WeatherCondition.SNOW
    if "fog" in description or "mist" in description:
        return WeatherCondition.FOG
    if "partly cloudy" in description:
        return WeatherCondition.PARTLY_CLOUDY
    if "cloud" in description or "overcast" in description:
        return WeatherCondition.CLOUDY
    if "clear" in description or "sunny" in description:
        return WeatherCondition.CLEAR
    return WeatherCondition.UNKNOWN


def _int(data: JsonObject, key: str) -> int:
    return int(data[key])


def _float(data: JsonObject, key: str) -> float:
    return float(data[key])
