"""JSON file cache for the latest normalized weather snapshot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from weather_morning_report.models import (
    CurrentConditions,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherCondition,
    WeatherSnapshot,
)

JsonObject = dict[str, Any]
CACHE_SCHEMA_VERSION = 1


class CacheError(RuntimeError):
    """Raised when no usable cached snapshot is available."""


class SnapshotCache:
    def __init__(self, path: Path, max_age: timedelta) -> None:
        self.path = path
        self.max_age = max_age

    def save(self, snapshot: WeatherSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(_snapshot_to_dict(snapshot), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def load(self, now: datetime) -> WeatherSnapshot:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            snapshot = _snapshot_from_dict(payload)
        except FileNotFoundError as exc:
            raise CacheError("cached weather snapshot does not exist") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise CacheError(f"cached weather snapshot is invalid: {exc}") from exc

        age = now - snapshot.fetched_at.astimezone(now.tzinfo)
        if age < timedelta(0):
            raise CacheError("cached weather snapshot is from the future")
        if age > self.max_age:
            raise CacheError(
                f"cached weather snapshot is stale ({age.total_seconds() / 3600:.1f} hours old)"
            )
        return snapshot


def _snapshot_to_dict(snapshot: WeatherSnapshot) -> JsonObject:
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "location": {
            "name": snapshot.location.name,
            "latitude": None,
            "longitude": None,
        },
        "source": snapshot.source,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "current": {
            "observed_at": snapshot.current.observed_at.isoformat(),
            "condition": snapshot.current.condition.value,
            "description": snapshot.current.description,
            "temperature_c": snapshot.current.temperature_c,
            "feels_like_c": snapshot.current.feels_like_c,
            "humidity_percent": snapshot.current.humidity_percent,
            "wind_speed_kph": snapshot.current.wind_speed_kph,
            "wind_direction": snapshot.current.wind_direction,
            "uv_index": snapshot.current.uv_index,
        },
        "daily": {
            "forecast_date": snapshot.daily.forecast_date.isoformat(),
            "minimum_temperature_c": snapshot.daily.minimum_temperature_c,
            "maximum_temperature_c": snapshot.daily.maximum_temperature_c,
            "uv_index": snapshot.daily.uv_index,
        },
        "hourly": [
            {
                "forecast_at": point.forecast_at.isoformat(),
                "condition": point.condition.value,
                "description": point.description,
                "temperature_c": point.temperature_c,
                "feels_like_c": point.feels_like_c,
                "precipitation_probability_percent": point.precipitation_probability_percent,
                "precipitation_mm": point.precipitation_mm,
                "thunder_probability_percent": point.thunder_probability_percent,
                "humidity_percent": point.humidity_percent,
                "wind_speed_kph": point.wind_speed_kph,
                "uv_index": point.uv_index,
            }
            for point in snapshot.hourly
        ],
        "air_quality": None,
        "warnings": [],
    }


def _snapshot_from_dict(data: JsonObject) -> WeatherSnapshot:
    if data["schema_version"] != CACHE_SCHEMA_VERSION:
        raise ValueError("unsupported cache schema version")
    location = data["location"]
    current = data["current"]
    daily = data["daily"]
    return WeatherSnapshot(
        location=Location(name=location["name"]),
        source=data["source"],
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        current=CurrentConditions(
            observed_at=datetime.fromisoformat(current["observed_at"]),
            condition=WeatherCondition(current["condition"]),
            description=current["description"],
            temperature_c=current["temperature_c"],
            feels_like_c=current["feels_like_c"],
            humidity_percent=current["humidity_percent"],
            wind_speed_kph=current["wind_speed_kph"],
            wind_direction=current["wind_direction"],
            uv_index=current["uv_index"],
        ),
        daily=DailyForecast(
            forecast_date=datetime.fromisoformat(daily["forecast_date"]).date(),
            minimum_temperature_c=daily["minimum_temperature_c"],
            maximum_temperature_c=daily["maximum_temperature_c"],
            uv_index=daily["uv_index"],
        ),
        hourly=tuple(_hourly_from_dict(point) for point in data["hourly"]),
    )


def _hourly_from_dict(data: JsonObject) -> HourlyForecast:
    return HourlyForecast(
        forecast_at=datetime.fromisoformat(data["forecast_at"]),
        condition=WeatherCondition(data["condition"]),
        description=data["description"],
        temperature_c=data["temperature_c"],
        feels_like_c=data["feels_like_c"],
        precipitation_probability_percent=data["precipitation_probability_percent"],
        precipitation_mm=data["precipitation_mm"],
        thunder_probability_percent=data["thunder_probability_percent"],
        humidity_percent=data["humidity_percent"],
        wind_speed_kph=data["wind_speed_kph"],
        uv_index=data["uv_index"],
    )
