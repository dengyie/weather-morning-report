import sqlite3
import stat
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select

from weather_morning_report.database.core import (
    DatabaseConfig,
    create_sqlite_engine,
    open_session,
    schema_is_current,
)
from weather_morning_report.database.models import (
    Admin,
    AppMeta,
    NotificationSettings,
    ProviderSettings,
    SessionRecord,
    SmtpSettings,
)
from weather_morning_report.database.operations import (
    check_consistency,
    initialize_installation,
    reset_admin_password,
    restore_installation,
    upgrade_installation,
)
from weather_morning_report.database.security import (
    decrypt_secret,
    encrypt_secret,
    verify_password,
)


def database_config(tmp_path) -> DatabaseConfig:
    return DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")


def initialize(config: DatabaseConfig) -> None:
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )


def test_initialize_creates_complete_schema_and_restricted_key(tmp_path) -> None:
    config = database_config(tmp_path)

    initialize(config)

    tables = set(inspect(create_sqlite_engine(config.path)).get_table_names())
    assert {
        "app_meta",
        "admin",
        "sessions",
        "recipients",
        "schedules",
        "smtp_settings",
        "provider_settings",
        "jobs",
        "run_history",
        "action_signals",
        "worker_lease",
        "audit_events",
        "backups",
    } <= tables
    assert schema_is_current(config.path)
    assert stat.S_IMODE(config.path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(config.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(config.secret_key_file.stat().st_mode) == 0o600
    with sqlite3.connect(config.path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0002_manual_preview_digest",
        )


def test_initialize_refuses_to_overwrite_installation(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)

    with pytest.raises(ValueError, match="already initialized"):
        initialize(config)


def test_password_is_argon2_hashed_and_reset_revokes_sessions(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)
    with open_session(config.path) as session:
        admin = session.scalar(select(Admin))
        assert admin is not None
        assert admin.password_hash.startswith("$argon2")
        assert verify_password(admin.password_hash, "correct horse battery")
        session.add(
            SessionRecord(
                id="active-session",
                admin_id=admin.id,
                expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=12),
            )
        )
        session.commit()

    reset_admin_password(config, "different secure password")

    with open_session(config.path) as session:
        admin = session.scalar(select(Admin))
        assert admin is not None
        assert verify_password(admin.password_hash, "different secure password")
        assert session.scalar(select(SessionRecord)) is None


def test_encrypted_secret_is_not_readable_from_database_value(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)

    encrypted = encrypt_secret(config.secret_key_file, "smtp-password")

    assert b"smtp-password" not in encrypted
    assert decrypt_secret(config.secret_key_file, encrypted) == "smtp-password"


def test_upgrade_preserves_backup_and_restore_recovers_database(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)
    backup = upgrade_installation(config)
    with sqlite3.connect(config.path) as connection:
        connection.execute("UPDATE app_meta SET default_timezone = 'Europe/London'")
        connection.commit()

    restore_installation(config, backup)

    check_consistency(config)
    with open_session(config.path) as session:
        assert session.get(AppMeta, 1).default_timezone == "Asia/Shanghai"


def test_consistency_requires_external_key(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)
    config.secret_key_file.unlink()

    with pytest.raises(ValueError, match="secret key is missing"):
        check_consistency(config)


def test_restore_rejects_invalid_source_without_replacing_active_database(tmp_path) -> None:
    config = database_config(tmp_path)
    initialize(config)
    invalid = tmp_path / "invalid.db"
    invalid.write_text("not sqlite", encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError):
        restore_installation(config, invalid)

    check_consistency(config)


def test_restore_without_external_key_generates_key_and_clears_credentials(tmp_path) -> None:
    source = database_config(tmp_path / "source")
    initialize(source)
    with open_session(source.path) as session:
        session.get(SmtpSettings, 1).encrypted_password = encrypt_secret(
            source.secret_key_file, "smtp-secret"
        )
        session.get(ProviderSettings, 1).encrypted_credentials = encrypt_secret(
            source.secret_key_file, "provider-secret"
        )
        session.get(NotificationSettings, 1).secret_key_backup_confirmed = True
        session.commit()
    backup = upgrade_installation(source)
    restored = database_config(tmp_path / "restored")

    restore_installation(restored, backup)

    check_consistency(restored)
    with open_session(restored.path) as session:
        assert session.get(SmtpSettings, 1).encrypted_password is None
        assert session.get(ProviderSettings, 1).encrypted_credentials is None
        assert session.get(NotificationSettings, 1).secret_key_backup_confirmed is False
