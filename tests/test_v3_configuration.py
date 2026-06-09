import pytest
from sqlalchemy import select

from weather_morning_report.configuration import (
    archive_recipient,
    create_default_schedule_for_recipient,
    load_configuration,
    restore_recipient,
    restore_schedule,
    save_branding,
    save_new_user_defaults,
    save_notifications,
    save_provider,
    save_recipient,
    save_schedule,
    save_smtp,
)
from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import AuditEvent, Schedule
from weather_morning_report.database.operations import initialize_installation
from weather_morning_report.database.security import decrypt_secret


def initialized_config(tmp_path) -> DatabaseConfig:
    config = DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )
    return config


def recipient(config: DatabaseConfig):
    return save_recipient(
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


def test_recipient_and_schedule_round_trip_with_audit(tmp_path) -> None:
    config = initialized_config(tmp_path)
    saved_recipient = recipient(config)
    saved_schedule = save_schedule(
        config.path,
        actor="admin",
        schedule_id=None,
        recipient_id=saved_recipient.id,
        local_send_time="08:30",
        report_type="morning",
        send_policy="always",
        enabled=True,
    )

    snapshot = load_configuration(config.path)

    assert snapshot.recipients[0].email == "alice@example.com"
    assert snapshot.schedules[0].id == saved_schedule.id
    with open_session(config.path) as session:
        events = session.scalars(select(AuditEvent.event_type)).all()
        assert "recipient_saved" in events
        assert "schedule_saved" in events


def test_new_user_defaults_round_trip_and_default_schedule(tmp_path) -> None:
    config = initialized_config(tmp_path)

    snapshot = load_configuration(config.path)
    assert snapshot.new_user_defaults.location_name == "Changning District, Shanghai"
    assert snapshot.new_user_defaults.location_query == "Changning,Shanghai"
    assert snapshot.new_user_defaults.local_send_time == "08:30"
    assert snapshot.new_user_defaults.schedule_enabled is True

    save_new_user_defaults(
        config.path,
        actor="admin",
        location_name="Beijing",
        location_query="Beijing",
        timezone="Asia/Shanghai",
        language="en",
        local_send_time="12:15",
        report_type="midday",
        send_policy="changes_only",
        schedule_enabled=False,
    )
    saved_recipient = recipient(config)
    schedule = create_default_schedule_for_recipient(
        config.path,
        actor="admin",
        recipient_id=saved_recipient.id,
    )

    defaults = load_configuration(config.path).new_user_defaults
    assert defaults.location_name == "Beijing"
    assert defaults.language == "en"
    assert schedule.local_send_time == "12:15"
    assert schedule.report_type == "midday"
    assert schedule.send_policy == "changes_only"
    assert schedule.enabled is False
    with open_session(config.path) as session:
        events = session.scalars(select(AuditEvent.event_type)).all()
        assert "new_user_defaults_saved" in events
        stored = session.scalar(
            select(Schedule).where(Schedule.recipient_id == saved_recipient.id)
        )
        assert stored.id == schedule.id


def test_new_user_defaults_validate_values(tmp_path) -> None:
    config = initialized_config(tmp_path)

    with pytest.raises(ValueError, match="default location name"):
        save_new_user_defaults(
            config.path,
            actor="admin",
            location_name="",
            location_query="Shanghai",
            timezone="Asia/Shanghai",
            language="zh-CN",
            local_send_time="08:30",
            report_type="morning",
            send_policy="always",
            schedule_enabled=True,
        )
    with pytest.raises(ValueError, match="local send time"):
        save_new_user_defaults(
            config.path,
            actor="admin",
            location_name="Shanghai",
            location_query="Shanghai",
            timezone="Asia/Shanghai",
            language="zh-CN",
            local_send_time="not-a-time",
            report_type="morning",
            send_policy="always",
            schedule_enabled=True,
        )


def test_archiving_recipient_archives_and_disables_schedules(tmp_path) -> None:
    config = initialized_config(tmp_path)
    saved_recipient = recipient(config)
    saved_schedule = save_schedule(
        config.path,
        actor="admin",
        schedule_id=None,
        recipient_id=saved_recipient.id,
        local_send_time="12:00",
        report_type="midday",
        send_policy="changes_only",
        enabled=True,
    )

    archive_recipient(config.path, saved_recipient.id, actor="admin")

    assert load_configuration(config.path).recipients == ()
    archived = load_configuration(config.path, include_archived=True)
    assert archived.recipients[0].enabled is False
    assert archived.schedules[0].enabled is False
    assert archived.schedules[0].archived_at is not None
    with pytest.raises(ValueError, match="restore the recipient"):
        restore_schedule(config.path, saved_schedule.id, actor="admin")
    restore_recipient(config.path, saved_recipient.id, actor="admin")
    restore_schedule(config.path, saved_schedule.id, actor="admin")
    assert len(load_configuration(config.path).schedules) == 1


def test_smtp_password_is_encrypted_and_blank_replacement_keeps_it(tmp_path) -> None:
    config = initialized_config(tmp_path)
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
    encrypted = load_configuration(config.path).smtp.encrypted_password
    save_smtp(
        config,
        actor="admin",
        host="smtp2.example.com",
        port=465,
        username="sender@example.com",
        password="",
        security="ssl",
        sender_email="sender@example.com",
    )

    assert load_configuration(config.path).smtp.encrypted_password == encrypted
    assert decrypt_secret(config.secret_key_file, encrypted) == "smtp-secret"
    assert b"smtp-secret" not in config.path.read_bytes()


def test_provider_credentials_are_encrypted(tmp_path) -> None:
    config = initialized_config(tmp_path)
    provider = load_configuration(config.path).providers[0]

    save_provider(
        config,
        provider.id,
        actor="admin",
        priority=5,
        enabled=True,
        credentials="provider-secret",
    )

    stored = load_configuration(config.path).providers[0]
    assert decrypt_secret(config.secret_key_file, stored.encrypted_credentials) == "provider-secret"
    assert b"provider-secret" not in config.path.read_bytes()


def test_branding_and_notification_validation(tmp_path) -> None:
    config = initialized_config(tmp_path)
    save_branding(
        config.path,
        actor="admin",
        report_title="Daily Weather",
        greeting_visible=False,
        footer_text="Take care",
        accent_color="#AABBCC",
        data_source_visible=False,
    )
    save_notifications(
        config.path,
        actor="admin",
        admin_email="admin@example.com",
        webhook_url="https://example.com/hook",
        webhook_enabled=True,
        retention_days=120,
        alert_cooldown_minutes=30,
        secret_key_backup_confirmed=True,
    )

    snapshot = load_configuration(config.path)
    assert snapshot.branding.accent_color == "#aabbcc"
    assert snapshot.notifications.retention_days == 120
    with pytest.raises(ValueError, match="accent color"):
        save_branding(
            config.path,
            actor="admin",
            report_title="Bad",
            greeting_visible=True,
            footer_text="",
            accent_color="red",
            data_source_visible=True,
        )
    with pytest.raises(ValueError, match="webhook URL"):
        save_notifications(
            config.path,
            actor="admin",
            admin_email="",
            webhook_url="file:///tmp/hook",
            webhook_enabled=True,
            retention_days=90,
            alert_cooldown_minutes=60,
            secret_key_backup_confirmed=False,
        )


@pytest.mark.parametrize(
    ("timezone", "language", "error"),
    [
        ("Invalid/Timezone", "zh-CN", "timezone is invalid"),
        ("Asia/Shanghai", "fr", "report language is invalid"),
    ],
)
def test_recipient_rejects_invalid_timezone_or_language(
    tmp_path, timezone, language, error
) -> None:
    config = initialized_config(tmp_path)

    with pytest.raises(ValueError, match=error):
        save_recipient(
            config.path,
            actor="admin",
            recipient_id=None,
            name="Alice",
            email="alice@example.com",
            location_name="Shanghai",
            location_query="Shanghai",
            timezone=timezone,
            language=language,
            enabled=True,
        )
