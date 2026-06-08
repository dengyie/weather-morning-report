"""V3 report execution, change detection, delivery, and run history."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from weather_morning_report.cache import SnapshotCache
from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import (
    ActionSignals as StoredActionSignals,
    BrandingSettings,
    Job,
    NotificationSettings,
    Recipient,
    RunHistory,
    Schedule,
    SmtpSettings,
    utc_now,
)
from weather_morning_report.database.security import decrypt_secret
from weather_morning_report.delivery.smtp import send_message
from weather_morning_report.jobs import ClaimedJob, begin_delivery
from weather_morning_report.providers.wttr import WttrProvider
from weather_morning_report.recommendations import ActionSignals, recommend
from weather_morning_report.rendering.html import render_html
from weather_morning_report.rendering.text import render_text
from weather_morning_report.service import load_snapshot
from weather_morning_report.settings import DeliverySettings

CACHE_MAX_AGE = timedelta(hours=12)


def signals_changed(previous: ActionSignals | None, candidate: ActionSignals) -> bool:
    return previous is None or previous != candidate


def report_digest(subject: str, text: str, html: str) -> str:
    normalized_text = re.sub(
        r"^(?:注意：实时天气源暂时不可用|Note: live providers are unavailable;).+?\n\n",
        "",
        text,
        flags=re.MULTILINE,
    )
    normalized_html = re.sub(
        r'<div class="notice">.*?</div>',
        "",
        html,
        flags=re.DOTALL,
    )
    return sha256(
        "\0".join((subject, normalized_text, normalized_html)).encode("utf-8")
    ).hexdigest()


def process_report_job(
    config: DatabaseConfig,
    job: ClaimedJob,
    *,
    sender=send_message,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(UTC)
    with open_session(config.path) as session:
        recipient = session.get(Recipient, job.recipient_id)
        schedule = session.get(Schedule, job.schedule_id) if job.schedule_id else None
        smtp = session.get(SmtpSettings, 1)
        notifications = session.get(NotificationSettings, 1)
        branding = session.get(BrandingSettings, 1)
        if recipient is None or recipient.archived_at is not None:
            raise ValueError("recipient does not exist or is archived")
        if smtp is None or notifications is None or branding is None:
            raise ValueError("delivery configuration is incomplete")
        send_policy = schedule.send_policy if schedule else "always"

    timezone = ZoneInfo(recipient.timezone)
    local_now = current.astimezone(timezone)
    result = load_snapshot(
        WttrProvider(
            location_name=recipient.location_name,
            location_query=recipient.location_query,
            timezone=timezone,
        ),
        SnapshotCache(_cache_path(config.path, recipient.location_query), CACHE_MAX_AGE),
        local_now,
    )
    advice = recommend(
        result.snapshot,
        report_date=local_now.date(),
        report_type=job.report_type,
        send_at=local_now,
        language=recipient.language,
    )
    subject = _branded_subject(advice.subject, branding.report_title)
    if job.kind == "automatic" and send_policy == "changes_only":
        previous = latest_sent_signals(
            config.path,
            recipient_id=recipient.id,
            report_type=job.report_type,
        )
        if not signals_changed(previous, advice.signals):
            record_run(
                config.path,
                job,
                recipient,
                status="skipped",
                subject=subject,
                signals=advice.signals,
                error_message="no meaningful weather change",
            )
            return "skipped"

    settings = _delivery_settings(config, smtp, notifications)
    render_options = {
        "greeting_visible": branding.greeting_visible,
        "footer_text": branding.footer_text,
        "data_source_visible": branding.data_source_visible,
    }
    text = render_text(
        result.snapshot,
        advice,
        cached=result.cached,
        recipient_name=recipient.name,
        language=recipient.language,
        report_type=job.report_type,
        **render_options,
    )
    html = render_html(
        result.snapshot,
        advice,
        cached=result.cached,
        recipient_name=recipient.name,
        language=recipient.language,
        report_type=job.report_type,
        accent_color=branding.accent_color,
        **render_options,
    )
    if job.kind == "manual" and job.preview_digest:
        if not secrets.compare_digest(job.preview_digest, report_digest(subject, text, html)):
            record_run(
                config.path,
                job,
                recipient,
                status="skipped",
                subject=subject,
                signals=advice.signals,
                error_code="manual_preview_changed",
                error_message="report changed after preview; generate and confirm a new preview",
            )
            return "skipped"
    message = _message(settings, recipient.email, subject, text, html)
    begin_delivery(config.path, job.id, job.lease_owner, now=current)
    sender(settings, message)
    record_run(
        config.path,
        job,
        recipient,
        status="sent",
        subject=subject,
        signals=advice.signals,
    )
    return "sent"


def preview_recipient_report(
    config: DatabaseConfig,
    *,
    recipient_id: int,
    report_type: str,
    now: datetime | None = None,
) -> tuple[str, str, str]:
    current = now or datetime.now(UTC)
    with open_session(config.path) as session:
        recipient = session.get(Recipient, recipient_id)
        branding = session.get(BrandingSettings, 1)
        if recipient is None or recipient.archived_at is not None:
            raise ValueError("recipient does not exist or is archived")
        if branding is None:
            raise ValueError("branding configuration is incomplete")
    timezone = ZoneInfo(recipient.timezone)
    local_now = current.astimezone(timezone)
    result = load_snapshot(
        WttrProvider(
            location_name=recipient.location_name,
            location_query=recipient.location_query,
            timezone=timezone,
        ),
        SnapshotCache(_cache_path(config.path, recipient.location_query), CACHE_MAX_AGE),
        local_now,
    )
    advice = recommend(
        result.snapshot,
        report_date=local_now.date(),
        report_type=report_type,
        send_at=local_now,
        language=recipient.language,
    )
    subject = _branded_subject(advice.subject, branding.report_title)
    options = {
        "cached": result.cached,
        "recipient_name": recipient.name,
        "language": recipient.language,
        "report_type": report_type,
        "greeting_visible": branding.greeting_visible,
        "footer_text": branding.footer_text,
        "data_source_visible": branding.data_source_visible,
    }
    text = render_text(result.snapshot, advice, **options)
    html = render_html(
        result.snapshot,
        advice,
        accent_color=branding.accent_color,
        **options,
    )
    return subject, text, html


def latest_sent_signals(
    path: Path,
    *,
    recipient_id: int,
    report_type: str,
) -> ActionSignals | None:
    with open_session(path) as session:
        stored = session.scalar(
            select(StoredActionSignals)
            .join(RunHistory, StoredActionSignals.run_history_id == RunHistory.id)
            .join(Job, RunHistory.job_id == Job.id)
            .where(
                RunHistory.recipient_id == recipient_id,
                RunHistory.report_type == report_type,
                RunHistory.status == "sent",
                Job.kind == "automatic",
            )
            .order_by(RunHistory.finished_at.desc(), RunHistory.id.desc())
            .limit(1)
        )
        if stored is None:
            return None
        return ActionSignals(**json.loads(stored.signals_json))


def record_run(
    path: Path,
    job: ClaimedJob,
    recipient: Recipient,
    *,
    status: str,
    subject: str,
    signals: ActionSignals,
    error_code: str | None = None,
    error_message: str | None = None,
) -> RunHistory:
    with open_session(path) as session:
        history = RunHistory(
            job_id=job.id,
            recipient_id=recipient.id,
            schedule_id=job.schedule_id,
            status=status,
            report_type=job.report_type,
            recipient_name_snapshot=recipient.name,
            masked_email_snapshot=_mask_email(recipient.email),
            subject=subject,
            action_summary_json=json.dumps(asdict(signals), separators=(",", ":")),
            error_code=error_code,
            error_message=error_message,
            started_at=utc_now(),
            finished_at=utc_now(),
        )
        session.add(history)
        session.flush()
        session.add(
            StoredActionSignals(
                run_history_id=history.id,
                recipient_id=recipient.id,
                signals_json=json.dumps(asdict(signals), separators=(",", ":")),
            )
        )
        session.commit()
        return history


def record_failed_job(config: DatabaseConfig, job: ClaimedJob, error: Exception) -> None:
    with open_session(config.path) as session:
        recipient = session.get(Recipient, job.recipient_id)
        if recipient is None:
            return
        session.add(
            RunHistory(
                job_id=job.id,
                recipient_id=recipient.id,
                schedule_id=job.schedule_id,
                status="failed",
                report_type=job.report_type,
                recipient_name_snapshot=recipient.name,
                masked_email_snapshot=_mask_email(recipient.email),
                subject="",
                action_summary_json="{}",
                error_code=type(error).__name__[:100],
                error_message=str(error)[:1000],
                started_at=utc_now(),
                finished_at=utc_now(),
            )
        )
        session.commit()


def _delivery_settings(
    config: DatabaseConfig,
    smtp: SmtpSettings,
    notifications: NotificationSettings,
) -> DeliverySettings:
    password = (
        decrypt_secret(config.secret_key_file, smtp.encrypted_password)
        if smtp.encrypted_password
        else ""
    )
    settings = DeliverySettings(
        admin_email=notifications.admin_email,
        sender_email=smtp.sender_email,
        smtp_host=smtp.host,
        smtp_port=smtp.port,
        smtp_username=smtp.username,
        smtp_password=password,
        smtp_security=smtp.security,
    )
    if not settings.sender_email or not settings.smtp_host:
        raise ValueError("SMTP sender email and host are required")
    return settings


def _message(
    settings: DeliverySettings,
    recipient_email: str,
    subject: str,
    text: str,
    html: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender_email
    message["To"] = recipient_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _cache_path(database_path: Path, location_query: str) -> Path:
    digest = sha256(location_query.encode("utf-8")).hexdigest()[:12]
    return database_path.parent / "weather-cache" / f"{digest}.json"


def _mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    visible = local[:1]
    return f"{visible}***@{domain}"


def _branded_subject(subject: str, report_title: str) -> str:
    prefix, separator, _ = subject.partition("] ")
    return f"{prefix}] {report_title}" if separator else report_title
