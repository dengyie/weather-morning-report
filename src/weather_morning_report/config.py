"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class Config:
    timezone: ZoneInfo
    location_name: str
    location_query: str
    cache_path: Path
    cache_max_age: timedelta
    settings_path: Path

    @classmethod
    def from_env(cls) -> Config:
        timezone_name = os.getenv("TIMEZONE", "Asia/Shanghai")
        location_name = os.getenv(
            "LOCATION_NAME",
            "Changning District, Shanghai",
        ).strip()
        location_query = os.getenv("LOCATION_QUERY", "Changning,Shanghai").strip()
        cache_path = Path(os.getenv("CACHE_PATH", "var/weather_snapshot.json"))
        settings_path = Path(os.getenv("SETTINGS_PATH", "var/settings.json"))
        cache_max_age_hours = float(os.getenv("CACHE_MAX_AGE_HOURS", "12"))
        if not location_name:
            raise ValueError("LOCATION_NAME must not be empty")
        if not location_query:
            raise ValueError("LOCATION_QUERY must not be empty")
        if cache_max_age_hours <= 0:
            raise ValueError("CACHE_MAX_AGE_HOURS must be greater than zero")
        return cls(
            timezone=ZoneInfo(timezone_name),
            location_name=location_name,
            location_query=location_query,
            cache_path=cache_path,
            cache_max_age=timedelta(hours=cache_max_age_hours),
            settings_path=settings_path,
        )
