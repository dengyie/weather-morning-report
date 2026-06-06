"""Application orchestration."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

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
from weather_morning_report.settings import (
    DeliverySettings,
    RecipientSettings,
    load_delivery_settings,
    load_preview_recipient,
)


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


def validate_configuration(config: Config) -> str:
    settings = load_delivery_settings(config.settings_path)
    settings.validate(require_complete=True)
    recipients = effective_recipients(settings, config)
    locations = {
        (recipient.location_name, recipient.location_query): recipient
        for recipient in recipients
    }
    sources = {_provider(config, recipient).fetch().source for recipient in locations.values()}
    return (
        "Configuration is valid; weather provider reachable via "
        + ", ".join(sorted(sources))
        + "."
    )


def preview(config: Config, *, output_format: str = "text") -> str:
    preview_recipient = load_preview_recipient(config.settings_path)
    recipient_name = preview_recipient.name if preview_recipient else ""
    provider = (
        _provider(config, preview_recipient)
        if preview_recipient
        else WttrProvider(
            location_name=config.location_name,
            location_query=config.location_query,
            timezone=config.timezone,
        )
    )
    cache = SnapshotCache(
        _cache_path(
            config.cache_path,
            preview_recipient,
            location_specific=bool(
                preview_recipient
                and preview_recipient.location_name
                and preview_recipient.location_query
            ),
        )
        if preview_recipient
        else config.cache_path,
        config.cache_max_age,
    )
    now = datetime.now(config.timezone)
    result = load_snapshot(provider, cache, now)
    advice = recommend(result.snapshot, report_date=now.date())
    if output_format == "html":
        return render_html(
            result.snapshot,
            advice,
            cached=result.cached,
            recipient_name=recipient_name,
        )
    if output_format == "text":
        return render_text(
            result.snapshot,
            advice,
            cached=result.cached,
            recipient_name=recipient_name,
        )
    raise ValueError(f"unsupported output format: {output_format}")


def send_report(config: Config) -> str:
    settings = load_delivery_settings(config.settings_path)
    settings.validate(require_complete=True)
    now = datetime.now(config.timezone)
    recipients = effective_recipients(settings, config)
    results: dict[tuple[str, str], SnapshotResult | ProviderError] = {}
    sent = 0
    failed_locations: set[tuple[str, str]] = set()
    for recipient in recipients:
        location = (recipient.location_name, recipient.location_query)
        if location not in results:
            try:
                results[location] = load_snapshot(
                    _provider(config, recipient),
                    SnapshotCache(
                        _cache_path(
                            config.cache_path,
                            recipient,
                            location_specific=bool(settings.recipients),
                        ),
                        config.cache_max_age,
                    ),
                    now,
                )
            except ProviderError as exc:
                results[location] = ProviderError(
                    f"{recipient.location_name}: {exc}"
                )
        result = results[location]
        if isinstance(result, ProviderError):
            if location not in failed_locations:
                notify_admin_failure(settings, result)
                failed_locations.add(location)
            continue
        advice = recommend(result.snapshot, report_date=now.date())
        message = build_report_message(
            settings,
            recipient=recipient,
            subject=advice.subject,
            text=render_text(
                result.snapshot,
                advice,
                cached=result.cached,
                recipient_name=recipient.name,
            ),
            html=render_html(
                result.snapshot,
                advice,
                cached=result.cached,
                recipient_name=recipient.name,
            ),
        )
        send_message(settings, message)
        sent += 1
    if not sent:
        return f"Weather reports skipped; administrator notified at {settings.admin_email}."
    return f"Weather reports sent to {sent} recipient(s)."


def notify_admin_failure(settings: DeliverySettings, error: Exception) -> None:
    send_message(settings, build_admin_failure_message(settings, error))


def effective_recipients(
    settings: DeliverySettings,
    config: Config,
) -> tuple[RecipientSettings, ...]:
    recipients = settings.recipients or (
        RecipientSettings(settings.recipient_name, settings.recipient_email),
    )
    return tuple(
        RecipientSettings(
            recipient.name,
            recipient.email,
            recipient.location_name or config.location_name,
            recipient.location_query or config.location_query,
        )
        for recipient in recipients
    )


def _provider(config: Config, recipient: RecipientSettings) -> WttrProvider:
    return WttrProvider(
        location_name=recipient.location_name or config.location_name,
        location_query=recipient.location_query or config.location_query,
        timezone=config.timezone,
    )


def _cache_path(
    base_path: Path,
    recipient: RecipientSettings,
    *,
    location_specific: bool,
) -> Path:
    if not location_specific:
        return base_path
    digest = sha256(recipient.location_query.encode("utf-8")).hexdigest()[:12]
    return base_path.with_name(f"{base_path.stem}-{digest}{base_path.suffix}")
