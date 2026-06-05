from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from weather_morning_report.models import WeatherCondition
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.providers.wttr import WttrProvider, parse_wttr_payload


SHANGHAI = ZoneInfo("Asia/Shanghai")
FETCHED_AT = datetime(2026, 6, 6, 8, 30, tzinfo=SHANGHAI)


def payload(
    *,
    morning_rain: int = 0,
    midday_rain: int = 70,
    evening_rain: int = 0,
    uv: int = 8,
) -> dict:
    def hour(time: str, rain: int, description: str, hour_uv: int) -> dict:
        return {
            "time": time,
            "tempC": "27",
            "FeelsLikeC": "29",
            "chanceofrain": str(rain),
            "chanceofthunder": "0",
            "precipMM": "0.2" if rain else "0",
            "humidity": "75",
            "uvIndex": str(hour_uv),
            "weatherDesc": [{"value": description}],
            "windspeedKmph": "12",
        }

    return {
        "current_condition": [
            {
                "temp_C": "26",
                "FeelsLikeC": "28",
                "humidity": "72",
                "uvIndex": "2",
                "weatherDesc": [{"value": "Partly cloudy"}],
                "windspeedKmph": "10",
                "winddir16Point": "E",
            }
        ],
        "weather": [
            {
                "date": "2026-06-06",
                "mintempC": "23",
                "maxtempC": "31",
                "uvIndex": str(uv),
                "hourly": [
                    hour("900", morning_rain, "Light rain" if morning_rain else "Sunny", 5),
                    hour("1200", midday_rain, "Light drizzle", uv),
                    hour("1800", evening_rain, "Light rain" if evening_rain else "Cloudy", 0),
                ],
            }
        ],
    }


def test_parse_wttr_payload_normalizes_hourly_data() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="wttr.in",
        fetched_at=FETCHED_AT,
    )

    assert snapshot.current.condition is WeatherCondition.PARTLY_CLOUDY
    assert [point.forecast_at.hour for point in snapshot.hourly] == [9, 12, 18]
    assert snapshot.hourly[1].condition is WeatherCondition.DRIZZLE
    assert snapshot.daily.uv_index == 8


def test_parse_wttr_payload_requires_hourly_forecast() -> None:
    invalid = payload()
    invalid["weather"][0]["hourly"] = []

    with pytest.raises(ProviderError, match="hourly forecast is empty"):
        parse_wttr_payload(
            invalid,
            location_name="Changning District, Shanghai",
            timezone=SHANGHAI,
            source="wttr.in",
            fetched_at=FETCHED_AT,
        )


def test_provider_falls_back_to_second_host(monkeypatch) -> None:
    provider = WttrProvider(
        "Changning District, Shanghai",
        "Changning,Shanghai",
        SHANGHAI,
        hosts=("primary", "fallback"),
    )

    def request(host: str) -> dict:
        if host == "primary":
            raise ProviderError("offline")
        return payload()

    monkeypatch.setattr(provider, "_request", request)

    assert provider.fetch().source == "fallback"

