"""Application orchestration."""

from dataclasses import dataclass
from datetime import datetime

from weather_morning_report.cache import CacheError, SnapshotCache
from weather_morning_report.config import Config
from weather_morning_report.models import WeatherSnapshot
from weather_morning_report.providers.base import ProviderError, WeatherProvider
from weather_morning_report.providers.wttr import WttrProvider
from weather_morning_report.recommendations import recommend
from weather_morning_report.rendering.text import render_text


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    snapshot: WeatherSnapshot
    cached: bool


def load_snapshot(
    provider: WeatherProvider,
    cache: SnapshotCache,
    now: datetime,
) -> SnapshotResult:
    try:
        snapshot = provider.fetch()
    except ProviderError as provider_error:
        try:
            return SnapshotResult(cache.load(now), cached=True)
        except CacheError as cache_error:
            raise ProviderError(
                f"weather providers failed and cache is unavailable: {cache_error}"
            ) from provider_error
    cache.save(snapshot)
    return SnapshotResult(snapshot, cached=False)


def preview(config: Config) -> str:
    provider = WttrProvider(
        location_name=config.location_name,
        location_query=config.location_query,
        timezone=config.timezone,
    )
    cache = SnapshotCache(config.cache_path, config.cache_max_age)
    result = load_snapshot(provider, cache, datetime.now(config.timezone))
    return render_text(
        result.snapshot,
        recommend(result.snapshot),
        cached=result.cached,
    )
