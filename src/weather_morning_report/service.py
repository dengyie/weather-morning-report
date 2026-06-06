"""Application orchestration."""

from dataclasses import dataclass
from datetime import datetime

from weather_morning_report.cache import CacheError, SnapshotCache
from weather_morning_report.config import Config
from weather_morning_report.delivery.messages import (
    build_admin_failure_message,
    build_report_message,
)
from weather_morning_report.delivery.smtp import send_message
from weather_morning_report.models import WeatherSnapshot
from weather_morning_report.providers.base import ProviderError, WeatherProvider
from weather_morning_report.providers.wttr import WttrProvider
from weather_morning_report.recommendations import recommend
from weather_morning_report.rendering.html import render_html
from weather_morning_report.rendering.text import render_text
from weather_morning_report.settings import DeliverySettings, load_delivery_settings


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


def preview(config: Config, *, output_format: str = "text") -> str:
    provider = WttrProvider(
        location_name=config.location_name,
        location_query=config.location_query,
        timezone=config.timezone,
    )
    cache = SnapshotCache(config.cache_path, config.cache_max_age)
    result = load_snapshot(provider, cache, datetime.now(config.timezone))
    advice = recommend(result.snapshot)
    if output_format == "html":
        return render_html(result.snapshot, advice, cached=result.cached)
    if output_format == "text":
        return render_text(result.snapshot, advice, cached=result.cached)
    raise ValueError(f"unsupported output format: {output_format}")


def send_report(config: Config) -> str:
    settings = load_delivery_settings(config.settings_path)
    settings.validate(require_complete=True)
    provider = WttrProvider(
        location_name=config.location_name,
        location_query=config.location_query,
        timezone=config.timezone,
    )
    cache = SnapshotCache(config.cache_path, config.cache_max_age)
    try:
        result = load_snapshot(provider, cache, datetime.now(config.timezone))
    except ProviderError as exc:
        notify_admin_failure(settings, exc)
        return f"Weather report skipped; administrator notified at {settings.admin_email}."
    advice = recommend(result.snapshot)
    message = build_report_message(
        settings,
        subject=advice.subject,
        text=render_text(result.snapshot, advice, cached=result.cached),
        html=render_html(result.snapshot, advice, cached=result.cached),
    )
    send_message(settings, message)
    return f"Weather report sent to {settings.recipient_email}."


def notify_admin_failure(settings: DeliverySettings, error: Exception) -> None:
    send_message(settings, build_admin_failure_message(settings, error))
