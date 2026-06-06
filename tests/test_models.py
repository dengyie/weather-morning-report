from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from weather_morning_report.models import (
    CurrentConditions,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherCondition,
    WeatherSnapshot,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def at(hour: int) -> datetime:
    return datetime(2026, 6, 6, hour, tzinfo=SHANGHAI)


def hourly(hour: int) -> HourlyForecast:
    return HourlyForecast(
        forecast_at=at(hour),
        condition=WeatherCondition.PARTLY_CLOUDY,
        description="Partly cloudy",
        temperature_c=27,
        feels_like_c=29,
        precipitation_probability_percent=20,
        precipitation_mm=0,
        thunder_probability_percent=0,
        humidity_percent=70,
        wind_speed_kph=12,
        uv_index=5,
    )


def snapshot(*points: HourlyForecast) -> WeatherSnapshot:
    return WeatherSnapshot(
        location=Location("Changning District, Shanghai"),
        source="wttr.in",
        fetched_at=at(8) + timedelta(minutes=30),
        current=CurrentConditions(
            observed_at=at(8),
            condition=WeatherCondition.PARTLY_CLOUDY,
            description="Partly cloudy",
            temperature_c=26,
            feels_like_c=28,
            humidity_percent=72,
            wind_speed_kph=10,
            uv_index=2,
        ),
        daily=DailyForecast(
            forecast_date=date(2026, 6, 6),
            minimum_temperature_c=23,
            maximum_temperature_c=31,
            uv_index=8,
        ),
        hourly=tuple(points),
    )


def test_snapshot_accepts_normalized_weather_data() -> None:
    report = snapshot(hourly(9), hourly(12), hourly(18))

    assert report.source == "wttr.in"
    assert report.daily.maximum_temperature_c == 31
    assert report.hourly[1].uv_index == 5


def test_snapshot_rejects_unsorted_hourly_forecasts() -> None:
    with pytest.raises(ValueError, match="ordered"):
        snapshot(hourly(12), hourly(9))


def test_snapshot_rejects_duplicate_hourly_forecasts() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        snapshot(hourly(9), hourly(9))


def test_models_reject_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        CurrentConditions(
            observed_at=datetime(2026, 6, 6, 8),
            condition=WeatherCondition.CLEAR,
            description="Clear",
            temperature_c=25,
            feels_like_c=26,
        )


@pytest.mark.parametrize("probability", [-1, 101])
def test_hourly_forecast_rejects_invalid_probability(probability: int) -> None:
    with pytest.raises(ValueError, match="precipitation_probability_percent"):
        HourlyForecast(
            forecast_at=at(9),
            condition=WeatherCondition.RAIN,
            description="Rain",
            temperature_c=24,
            feels_like_c=25,
            precipitation_probability_percent=probability,
        )


def test_daily_forecast_rejects_inverted_temperature_range() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        DailyForecast(
            forecast_date=date(2026, 6, 6),
            minimum_temperature_c=32,
            maximum_temperature_c=25,
        )


def test_snapshot_rejects_observation_after_fetch() -> None:
    with pytest.raises(ValueError, match="later than fetched_at"):
        WeatherSnapshot(
            location=Location("Changning District, Shanghai"),
            source="wttr.in",
            fetched_at=at(8),
            current=CurrentConditions(
                observed_at=at(9),
                condition=WeatherCondition.CLEAR,
                description="Clear",
                temperature_c=25,
                feels_like_c=25,
            ),
            daily=DailyForecast(
                forecast_date=date(2026, 6, 6),
                minimum_temperature_c=20,
                maximum_temperature_c=30,
            ),
        )
