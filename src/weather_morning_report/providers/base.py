"""Provider contracts and errors."""

from __future__ import annotations

from typing import Protocol

from weather_morning_report.models import WeatherSnapshot


class ProviderError(RuntimeError):
    """Raised when a provider cannot return a valid normalized snapshot."""


class WeatherProvider(Protocol):
    def fetch(self) -> WeatherSnapshot: ...

