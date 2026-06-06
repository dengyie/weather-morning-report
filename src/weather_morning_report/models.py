"""Provider-independent weather domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_range(
    value: float | int | None,
    minimum: float,
    maximum: float,
    field_name: str,
) -> None:
    if value is not None and not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")


class WeatherCondition(StrEnum):
    """Normalized conditions used by recommendation rules."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    SLEET = "sleet"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Location:
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("location name must not be empty")


@dataclass(frozen=True, slots=True)
class CurrentConditions:
    observed_at: datetime
    condition: WeatherCondition
    description: str
    temperature_c: float
    feels_like_c: float
    humidity_percent: int | None = None
    wind_speed_kph: float | None = None
    wind_direction: str | None = None
    uv_index: float | None = None

    def __post_init__(self) -> None:
        _require_aware(self.observed_at, "observed_at")
        _require_range(self.humidity_percent, 0, 100, "humidity_percent")
        _require_range(self.wind_speed_kph, 0, 500, "wind_speed_kph")
        _require_range(self.uv_index, 0, 30, "uv_index")


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    forecast_at: datetime
    condition: WeatherCondition
    description: str
    temperature_c: float
    feels_like_c: float
    precipitation_probability_percent: int | None = None
    precipitation_mm: float | None = None
    thunder_probability_percent: int | None = None
    humidity_percent: int | None = None
    wind_speed_kph: float | None = None
    uv_index: float | None = None

    def __post_init__(self) -> None:
        _require_aware(self.forecast_at, "forecast_at")
        _require_range(
            self.precipitation_probability_percent,
            0,
            100,
            "precipitation_probability_percent",
        )
        _require_range(self.precipitation_mm, 0, 2_000, "precipitation_mm")
        _require_range(
            self.thunder_probability_percent,
            0,
            100,
            "thunder_probability_percent",
        )
        _require_range(self.humidity_percent, 0, 100, "humidity_percent")
        _require_range(self.wind_speed_kph, 0, 500, "wind_speed_kph")
        _require_range(self.uv_index, 0, 30, "uv_index")


@dataclass(frozen=True, slots=True)
class DailyForecast:
    forecast_date: date
    minimum_temperature_c: float
    maximum_temperature_c: float
    uv_index: float | None = None

    def __post_init__(self) -> None:
        if self.minimum_temperature_c > self.maximum_temperature_c:
            raise ValueError(
                "minimum_temperature_c must not exceed maximum_temperature_c"
            )
        _require_range(self.uv_index, 0, 30, "uv_index")


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    """A validated, normalized snapshot from one weather provider."""

    location: Location
    source: str
    fetched_at: datetime
    current: CurrentConditions
    daily: DailyForecast
    hourly: tuple[HourlyForecast, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        _require_aware(self.fetched_at, "fetched_at")
        if self.current.observed_at > self.fetched_at:
            raise ValueError("current observation must not be later than fetched_at")

        forecast_times = [point.forecast_at for point in self.hourly]
        if forecast_times != sorted(forecast_times):
            raise ValueError("hourly forecasts must be ordered by forecast_at")
        if len(forecast_times) != len(set(forecast_times)):
            raise ValueError("hourly forecasts must not contain duplicate times")

