"""Validated v3 business configuration stored in SQLite."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import time
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import (
    AuditEvent,
    BrandingSettings,
    NotificationSettings,
    ProviderSettings,
    Recipient,
    Schedule,
    SmtpSettings,
    utc_now,
)
from weather_morning_report.database.security import encrypt_secret

REPORT_TYPES = {"morning", "midday", "evening"}
SEND_POLICIES = {"always", "changes_only"}
LANGUAGES = {"zh-CN", "en"}
SMTP_SECURITY = {"starttls", "ssl", "plain"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True, slots=True)
class ConfigurationSnapshot:
    recipients: tuple[Recipient, ...]
    schedules: tuple[Schedule, ...]
    smtp: SmtpSettings
    providers: tuple[ProviderSettings, ...]
    branding: BrandingSettings
    notifications: NotificationSettings


def load_configuration(path: Path, *, include_archived: bool = False) -> ConfigurationSnapshot:
    with open_session(path) as session:
        recipient_query = select(Recipient).order_by(Recipient.name, Recipient.id)
        schedule_query = select(Schedule).order_by(Schedule.recipient_id, Schedule.local_send_time)
        if not include_archived:
            recipient_query = recipient_query.where(Recipient.archived_at.is_(None))
            schedule_query = schedule_query.where(Schedule.archived_at.is_(None))
        return ConfigurationSnapshot(
            recipients=tuple(session.scalars(recipient_query)),
            schedules=tuple(session.scalars(schedule_query)),
            smtp=_singleton(session, SmtpSettings),
            providers=tuple(
                session.scalars(select(ProviderSettings).order_by(ProviderSettings.priority))
            ),
            branding=_singleton(session, BrandingSettings),
            notifications=_singleton(session, NotificationSettings),
        )


def save_recipient(
    path: Path,
    *,
    actor: str,
    recipient_id: int | None,
    name: str,
    email: str,
    location_name: str,
    location_query: str,
    timezone: str,
    language: str,
    enabled: bool,
) -> Recipient:
    values = {
        "name": _required(name, "recipient name"),
        "email": _email(email, "recipient email"),
        "location_name": _required(location_name, "location name"),
        "location_query": _required(location_query, "location query"),
        "timezone": _timezone(timezone),
        "language": _choice(language, LANGUAGES, "report language"),
        "enabled": enabled,
    }
    with open_session(path) as session:
        recipient = session.get(Recipient, recipient_id) if recipient_id else Recipient(**values)
        if recipient_id and recipient is None:
            raise ValueError("recipient does not exist")
        for field, value in values.items():
            setattr(recipient, field, value)
        recipient.updated_at = utc_now()
        session.add(recipient)
        _audit(session, actor, "recipient_saved", {"recipient_id": recipient_id})
        session.commit()
        return recipient


def archive_recipient(path: Path, recipient_id: int, *, actor: str) -> None:
    with open_session(path) as session:
        recipient = _get(session, Recipient, recipient_id, "recipient")
        recipient.archived_at = utc_now()
        recipient.enabled = False
        schedules = session.scalars(
            select(Schedule).where(Schedule.recipient_id == recipient_id)
        )
        for schedule in schedules:
            schedule.enabled = False
            schedule.archived_at = schedule.archived_at or utc_now()
        _audit(session, actor, "recipient_archived", {"recipient_id": recipient_id})
        session.commit()


def restore_recipient(path: Path, recipient_id: int, *, actor: str) -> None:
    with open_session(path) as session:
        recipient = _get(session, Recipient, recipient_id, "recipient")
        recipient.archived_at = None
        recipient.enabled = True
        _audit(session, actor, "recipient_restored", {"recipient_id": recipient_id})
        session.commit()


def save_schedule(
    path: Path,
    *,
    actor: str,
    schedule_id: int | None,
    recipient_id: int,
    local_send_time: str,
    report_type: str,
    send_policy: str,
    enabled: bool,
) -> Schedule:
    local_send_time = _parse_time(local_send_time)
    values = {
        "recipient_id": recipient_id,
        "local_send_time": local_send_time,
        "report_type": _choice(report_type, REPORT_TYPES, "report type"),
        "send_policy": _choice(send_policy, SEND_POLICIES, "send policy"),
        "enabled": enabled,
    }
    with open_session(path) as session:
        recipient = _get(session, Recipient, recipient_id, "recipient")
        if recipient.archived_at is not None:
            raise ValueError("cannot schedule an archived recipient")
        schedule = session.get(Schedule, schedule_id) if schedule_id else Schedule(**values)
        if schedule_id and schedule is None:
            raise ValueError("schedule does not exist")
        for field, value in values.items():
            setattr(schedule, field, value)
        schedule.updated_at = utc_now()
        session.add(schedule)
        _audit(session, actor, "schedule_saved", {"schedule_id": schedule_id})
        session.commit()
        return schedule


def archive_schedule(path: Path, schedule_id: int, *, actor: str) -> None:
    with open_session(path) as session:
        schedule = _get(session, Schedule, schedule_id, "schedule")
        schedule.enabled = False
        schedule.archived_at = utc_now()
        _audit(session, actor, "schedule_archived", {"schedule_id": schedule_id})
        session.commit()


def restore_schedule(path: Path, schedule_id: int, *, actor: str) -> None:
    with open_session(path) as session:
        schedule = _get(session, Schedule, schedule_id, "schedule")
        recipient = _get(session, Recipient, schedule.recipient_id, "recipient")
        if recipient.archived_at is not None:
            raise ValueError("restore the recipient before restoring its schedule")
        schedule.archived_at = None
        schedule.enabled = True
        _audit(session, actor, "schedule_restored", {"schedule_id": schedule_id})
        session.commit()


def save_smtp(
    config: DatabaseConfig,
    *,
    actor: str,
    host: str,
    port: int,
    username: str,
    password: str,
    security: str,
    sender_email: str,
) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("SMTP port must be between 1 and 65535")
    security = _choice(security, SMTP_SECURITY, "SMTP security")
    sender_email = _email(sender_email, "sender email") if sender_email.strip() else ""
    with open_session(config.path) as session:
        smtp = _singleton(session, SmtpSettings)
        smtp.host = host.strip()
        smtp.port = port
        smtp.username = username.strip()
        smtp.security = security
        smtp.sender_email = sender_email
        if password:
            smtp.encrypted_password = encrypt_secret(config.secret_key_file, password)
        smtp.updated_at = utc_now()
        _audit(session, actor, "smtp_saved")
        session.commit()


def save_provider(
    config: DatabaseConfig,
    provider_id: int,
    *,
    actor: str,
    priority: int,
    enabled: bool,
    credentials: str,
) -> None:
    if priority < 0:
        raise ValueError("provider priority must not be negative")
    with open_session(config.path) as session:
        provider = _get(session, ProviderSettings, provider_id, "provider")
        provider.priority = priority
        provider.enabled = enabled
        if credentials:
            provider.encrypted_credentials = encrypt_secret(
                config.secret_key_file, credentials
            )
        provider.updated_at = utc_now()
        _audit(session, actor, "provider_saved", {"provider_id": provider_id})
        session.commit()


def save_branding(
    path: Path,
    *,
    actor: str,
    report_title: str,
    greeting_visible: bool,
    footer_text: str,
    accent_color: str,
    data_source_visible: bool,
) -> None:
    if not HEX_COLOR.fullmatch(accent_color):
        raise ValueError("accent color must be a six-digit hex color")
    with open_session(path) as session:
        branding = _singleton(session, BrandingSettings)
        branding.report_title = _required(report_title, "report title")
        branding.greeting_visible = greeting_visible
        branding.footer_text = footer_text.strip()
        branding.accent_color = accent_color.lower()
        branding.data_source_visible = data_source_visible
        _audit(session, actor, "branding_saved")
        session.commit()


def save_notifications(
    path: Path,
    *,
    actor: str,
    admin_email: str,
    webhook_url: str,
    webhook_enabled: bool,
    retention_days: int,
    alert_cooldown_minutes: int,
    secret_key_backup_confirmed: bool,
) -> None:
    if not 1 <= retention_days <= 3650:
        raise ValueError("retention days must be between 1 and 3650")
    if not 1 <= alert_cooldown_minutes <= 10080:
        raise ValueError("alert cooldown must be between 1 and 10080 minutes")
    webhook_url = webhook_url.strip()
    if webhook_url and urlparse(webhook_url).scheme not in {"http", "https"}:
        raise ValueError("webhook URL must use http or https")
    with open_session(path) as session:
        settings = _singleton(session, NotificationSettings)
        settings.admin_email = _email(admin_email, "administrator email") if admin_email.strip() else ""
        settings.webhook_url = webhook_url
        settings.webhook_enabled = webhook_enabled
        settings.retention_days = retention_days
        settings.alert_cooldown_minutes = alert_cooldown_minutes
        settings.secret_key_backup_confirmed = secret_key_backup_confirmed
        _audit(session, actor, "notifications_saved")
        session.commit()


def _singleton(session, model):
    value = session.get(model, 1)
    if value is None:
        raise ValueError(f"{model.__tablename__} singleton is missing")
    return value


def _get(session, model, identifier: int, label: str):
    value = session.get(model, identifier)
    if value is None:
        raise ValueError(f"{label} does not exist")
    return value


def _audit(session, actor: str, event_type: str, details: dict | None = None) -> None:
    session.add(
        AuditEvent(
            event_type=event_type,
            actor=actor,
            details_json=json.dumps(details or {}, separators=(",", ":")),
        )
    )


def _required(value: str, label: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError(f"{label} must not be empty")
    return result


def _email(value: str, label: str) -> str:
    result = value.strip()
    _, address = parseaddr(result)
    local, separator, domain = address.rpartition("@")
    if not separator or not local or "." not in domain or domain.startswith("."):
        raise ValueError(f"{label} is invalid")
    return result


def _timezone(value: str) -> str:
    result = value.strip()
    try:
        ZoneInfo(result)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"recipient timezone is invalid: {result}") from exc
    return result


def _choice(value: str, choices: set[str], label: str) -> str:
    if value not in choices:
        raise ValueError(f"{label} is invalid")
    return value


def _parse_time(value: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("local send time must use HH:MM") from exc
    return parsed.strftime("%H:%M")
