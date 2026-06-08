from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from weather_morning_report import v3_service
from weather_morning_report.configuration import (
    save_branding,
    save_notifications,
    save_recipient,
    save_schedule,
    save_smtp,
)
from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import Job, RunHistory
from weather_morning_report.database.operations import initialize_installation
from weather_morning_report.jobs import (
    claim_job,
    complete_job,
    enqueue_due_jobs,
    enqueue_manual_job,
    fail_job,
)
from weather_morning_report.recommendations import ActionSignals
from weather_morning_report.service import SnapshotResult
from weather_morning_report.v3_service import (
    preview_recipient_report,
    process_report_job,
    record_failed_job,
    report_digest,
    signals_changed,
)
from test_service import weather_snapshot

NOW = datetime(2026, 6, 8, 0, 30, tzinfo=UTC)


def configured_database(tmp_path, *, policy="always") -> DatabaseConfig:
    config = DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )
    recipient = save_recipient(
        config.path,
        actor="admin",
        recipient_id=None,
        name="Alice",
        email="alice@example.com",
        location_name="Shanghai",
        location_query="Shanghai",
        timezone="Asia/Shanghai",
        language="zh-CN",
        enabled=True,
    )
    save_schedule(
        config.path,
        actor="admin",
        schedule_id=None,
        recipient_id=recipient.id,
        local_send_time="08:30",
        report_type="morning",
        send_policy=policy,
        enabled=True,
    )
    save_smtp(
        config,
        actor="admin",
        host="smtp.example.com",
        port=587,
        username="sender@example.com",
        password="smtp-secret",
        security="starttls",
        sender_email="sender@example.com",
    )
    save_notifications(
        config.path,
        actor="admin",
        admin_email="admin@example.com",
        webhook_url="",
        webhook_enabled=False,
        retention_days=90,
        alert_cooldown_minutes=60,
        secret_key_backup_confirmed=False,
    )
    return config


def stub_weather(monkeypatch) -> None:
    snapshot = weather_snapshot()
    monkeypatch.setattr(
        v3_service,
        "load_snapshot",
        lambda provider, cache, now: SnapshotResult(snapshot, cached=False),
    )


def test_signals_changed_compares_structured_levels() -> None:
    signals = ActionSignals(0, 0, 1, 2, 0, False, False, False)

    assert signals_changed(None, signals)
    assert not signals_changed(signals, signals)
    assert signals_changed(signals, ActionSignals(0, 1, 1, 2, 0, False, False, False))


def test_report_digest_ignores_cache_transport_notice() -> None:
    assert report_digest(
        "Subject",
        "Body",
        "<main>Body</main>",
    ) == report_digest(
        "Subject",
        "Note: live providers are unavailable; this report uses cached data.\n\nBody",
        '<div class="notice">using cached data</div><main>Body</main>',
    )


def test_worker_processor_sends_and_records_sanitized_history(tmp_path, monkeypatch) -> None:
    config = configured_database(tmp_path)
    stub_weather(monkeypatch)
    sent = []
    enqueue_due_jobs(config.path, now=NOW)
    job = claim_job(config.path, "worker", now=NOW)

    result = process_report_job(
        config,
        job,
        sender=lambda settings, message: sent.append((settings, message)),
        now=NOW,
    )

    assert result == "sent"
    assert sent[0][1]["To"] == "alice@example.com"
    assert sent[0][0].smtp_password == "smtp-secret"
    with open_session(config.path) as session:
        history = session.scalar(select(RunHistory))
        assert history.status == "sent"
        assert history.masked_email_snapshot == "a***@example.com"
        assert "alice@example.com" not in history.action_summary_json
        assert not hasattr(history, "html")


def test_delivery_exception_after_dispatch_stops_automatic_retry(
    tmp_path, monkeypatch
) -> None:
    config = configured_database(tmp_path)
    stub_weather(monkeypatch)
    enqueue_due_jobs(config.path, now=NOW)
    job = claim_job(config.path, "worker", now=NOW)

    try:
        process_report_job(
            config,
            job,
            sender=lambda settings, message: (_ for _ in ()).throw(
                RuntimeError("connection lost after DATA")
            ),
            now=NOW,
        )
    except RuntimeError as error:
        status = fail_job(
            config.path,
            job.id,
            "worker",
            error_code=type(error).__name__,
            error_message=str(error),
            now=NOW,
        )

    assert status == "failed"
    with open_session(config.path) as session:
        stored = session.get(Job, job.id)
        assert stored.last_error_code == "delivery_result_unknown"


def test_changes_only_skips_same_automatic_signals(tmp_path, monkeypatch) -> None:
    config = configured_database(tmp_path, policy="changes_only")
    stub_weather(monkeypatch)
    sent = []
    enqueue_due_jobs(config.path, now=NOW)
    first = claim_job(config.path, "worker", now=NOW)
    assert process_report_job(
        config, first, sender=lambda settings, message: sent.append(message), now=NOW
    ) == "sent"
    complete_job(config.path, first.id, "worker", now=NOW)

    tomorrow = NOW + timedelta(days=1)
    enqueue_due_jobs(config.path, now=tomorrow)
    second = claim_job(config.path, "worker", now=tomorrow)
    assert process_report_job(
        config, second, sender=lambda settings, message: sent.append(message), now=tomorrow
    ) == "skipped"

    assert len(sent) == 1
    with open_session(config.path) as session:
        statuses = session.scalars(select(RunHistory.status).order_by(RunHistory.id)).all()
        assert statuses == ["sent", "skipped"]


def test_manual_send_does_not_become_changes_only_baseline(tmp_path, monkeypatch) -> None:
    config = configured_database(tmp_path, policy="changes_only")
    stub_weather(monkeypatch)
    sent = []
    manual = enqueue_manual_job(config.path, recipient_id=1, report_type="morning", now=NOW)
    claimed_manual = claim_job(config.path, "worker", now=NOW)
    assert claimed_manual.id == manual.id
    assert process_report_job(
        config,
        claimed_manual,
        sender=lambda settings, message: sent.append(message),
        now=NOW,
    ) == "sent"
    complete_job(config.path, claimed_manual.id, "worker", now=NOW)

    enqueue_due_jobs(config.path, now=NOW)
    automatic = claim_job(config.path, "worker", now=NOW)
    assert process_report_job(
        config,
        automatic,
        sender=lambda settings, message: sent.append(message),
        now=NOW,
    ) == "sent"
    assert len(sent) == 2


def test_manual_send_skips_when_confirmed_preview_changed(tmp_path, monkeypatch) -> None:
    config = configured_database(tmp_path)
    stub_weather(monkeypatch)
    manual = enqueue_manual_job(
        config.path,
        recipient_id=1,
        report_type="morning",
        preview_digest="not-the-current-preview",
        now=NOW,
    )
    job = claim_job(config.path, "worker", now=NOW)
    sent = []

    result = process_report_job(
        config,
        job,
        sender=lambda settings, message: sent.append(message),
        now=NOW,
    )

    assert result == "skipped"
    assert sent == []
    with open_session(config.path) as session:
        history = session.scalar(select(RunHistory).where(RunHistory.job_id == manual.id))
        assert history.error_code == "manual_preview_changed"


def test_exhausted_failure_records_sanitized_history(tmp_path) -> None:
    config = configured_database(tmp_path)
    enqueue_due_jobs(config.path, now=NOW)
    job = claim_job(config.path, "worker", now=NOW)

    record_failed_job(config, job, RuntimeError("SMTP password leaked? no"))

    with open_session(config.path) as session:
        history = session.scalar(select(RunHistory))
        assert history.status == "failed"
        assert history.masked_email_snapshot == "a***@example.com"
        assert history.error_code == "RuntimeError"


def test_v3_preview_applies_branding_without_sending(tmp_path, monkeypatch) -> None:
    config = configured_database(tmp_path)
    stub_weather(monkeypatch)
    save_branding(
        config.path,
        actor="admin",
        report_title="My Forecast",
        greeting_visible=False,
        footer_text="Stay prepared",
        accent_color="#abcdef",
        data_source_visible=False,
    )

    subject, text, html = preview_recipient_report(
        config,
        recipient_id=1,
        report_type="evening",
        now=NOW,
    )

    assert subject.endswith("My Forecast")
    assert "晚上好" not in text
    assert "Stay prepared" in text
    assert "数据来源" not in text
    assert "#abcdef" in html
    assert "数据来源" not in html
