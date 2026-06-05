"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class Config:
    timezone: ZoneInfo
    location_name: str
    location_query: str

    @classmethod
    def from_env(cls) -> Config:
        timezone_name = os.getenv("TIMEZONE", "Asia/Shanghai")
        location_name = os.getenv(
            "LOCATION_NAME",
            "Changning District, Shanghai",
        ).strip()
        location_query = os.getenv("LOCATION_QUERY", "Changning,Shanghai").strip()
        if not location_name:
            raise ValueError("LOCATION_NAME must not be empty")
        if not location_query:
            raise ValueError("LOCATION_QUERY must not be empty")
        return cls(
            timezone=ZoneInfo(timezone_name),
            location_name=location_name,
            location_query=location_query,
        )

