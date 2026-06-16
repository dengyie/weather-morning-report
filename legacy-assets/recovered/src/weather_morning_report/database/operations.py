"""First-time setup, upgrades, restore, and administrator operations."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, func, select

from weather_morning_report.database.core import (
    APPLICATION_VERSION,
    SCHEMA_VERSION,
    TASK_PROTOCOL_VERSION,
    DatabaseConfig,
    open_session,
    schema_is_current,
    upgrade_database,
)
from weather_morning_report.database.models import (
    Admin,
    AppMeta,
    AuditEvent,
    BrandingSettings,
    NotificationSettings,
    ProviderSettings,
    SessionRecord,
    SmtpSettings,
    utc_now,
)
from weather_morning_report.database.security import (
    generate_secret_key,
    hash_password,
    load_cipher,
)


def initialize_installation(
    config: DatabaseConfig,
    *,
    username: str,
    password: str,
    default_timezone: str,
) -> None:
    if config.path.exists() or config.secret_key_file.exists():
        raise ValueError("installation is already initialized")
    _validate_timezone(default_timezone)
    _prepare_data_directory(config.path.parent)
    generate_secret_key(config.secret_key_file)
    try:
        upgrade_database(config.path)
        config.path.chmod(0o600)
        with open_session(config.path) as session:
            session.add(
                AppMeta(
                    id=1,
                    schema_version=SCHEMA_VERSION,
                    application_version=APPLICATION_VERSION,
                    task_protocol_version=TASK_PROTOCOL_VERSION,
                    default_timezone=default_timezone,
                )
            )
            session.add(Admin(username=_validate_username(username), password_hash=hash_password(password)))
            session.add(SmtpSettings(id=1))
            session.add(BrandingSettings(id=1))
            session.add(NotificationSettings(id=1))
            session.add_all(
                [
                    ProviderSettings(
                        provider_type="wttr.in",
                        priority=10,
                        enabled=True,
                    ),
                    ProviderSettings(
                        provider_type="wttr.is",
                        priority=20,
                        enabled=True,
                    ),
                ]
            )
            session.add(AuditEvent(event_type="installation_initialized", actor="local-cli"))
            session.commit()
        check_consistency(config)
    except Exception:
        config.path.unlink(missing_ok=True)
        _remove_sqlite_sidecars(config.path)
        config.secret_key_file.unlink(missing_ok=True)
        raise


def upgrade_installation(config: DatabaseConfig) -> Path:
    _require_installation(config)
    backup = backup_database(config.path, config.path.parent / "backups", "pre-upgrade")
    upgrade_database(config.path)
    config.path.chmod(0o600)
    with open_session(config.path) as session:
        meta = session.get(AppMeta, 1)
        if meta is None:
            raise ValueError("database app metadata is missing")
        meta.schema_version = SCHEMA_VERSION
        meta.application_version = APPLICATION_VERSION
        meta.task_protocol_version = TASK_PROTOCOL_VERSION
        meta.updated_at = utc_now()
        session.commit()
    check_consistency(config)
    return backup


def restore_installation(config: DatabaseConfig, source: Path) -> Path | None:
    if not source.is_file():
        raise ValueError(f"restore source does not exist: {source}")
    if source.resolve() == config.path.resolve():
        raise ValueError("restore source must not be the active database")
    _prepare_data_directory(config.path.parent)
    temporary = config.path.with_suffix(f"{config.path.suffix}.restore")
    temporary.unlink(missing_ok=True)
    _remove_sqlite_sidecars(temporary)
    generated_replacement_key = False
    restored = False
    try:
        _copy_database(source, temporary)
        upgrade_database(temporary)
        check_consistency(
            DatabaseConfig(temporary, config.secret_key_file),
            require_secret=False,
        )
        if not config.secret_key_file.is_file():
            generate_secret_key(config.secret_key_file)
            generated_replacement_key = True
            with open_session(temporary) as session:
                smtp = session.get(SmtpSettings, 1)
                if smtp:
                    smtp.encrypted_password = None
                for provider in session.scalars(select(ProviderSettings)):
                    provider.encrypted_credentials = None
                notifications = session.get(NotificationSettings, 1)
                if notifications:
                    notifications.secret_key_backup_confirmed = False
                session.add(
                    AuditEvent(
                        event_type="restore_generated_replacement_key",
                        actor="local-cli",
                    )
                )
                session.commit()
        backup = (
            backup_database(config.path, config.path.parent / "backups", "pre-restore")
            if config.path.exists()
            else None
        )
        _checkpoint_database(temporary)
        _remove_sqlite_sidecars(temporary)
        _remove_sqlite_sidecars(config.path)
        temporary.replace(config.path)
        config.path.chmod(0o600)
        check_consistency(config)
        restored = True
        return backup
    finally:
        temporary.unlink(missing_ok=True)
        _remove_sqlite_sidecars(temporary)
        if generated_replacement_key and not restored:
            config.secret_key_file.unlink(missing_ok=True)


def create_admin(config: DatabaseConfig, username: str, password: str) -> None:
    _require_installation(config)
    with open_session(config.path) as session:
        if session.scalar(select(func.count()).select_from(Admin)):
            raise ValueError("administrator account already exists")
        session.add(Admin(username=_validate_username(username), password_hash=hash_password(password)))
        session.add(AuditEvent(event_type="admin_created", actor="local-cli"))
        session.commit()


def reset_admin_password(config: DatabaseConfig, password: str) -> None:
    _require_installation(config)
    with open_session(config.path) as session:
        admin = session.scalar(select(Admin))
        if admin is None:
            raise ValueError("administrator account does not exist")
        admin.password_hash = hash_password(password)
        admin.password_changed_at = utc_now()
        session.execute(delete(SessionRecord))
        session.add(AuditEvent(event_type="admin_password_reset", actor="local-cli"))
        session.commit()


def backup_database(
    source: Path,
    directory: Path,
    kind: str,
    *,
    now: datetime | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    target = directory / f"weather-report-{kind}-{timestamp}.db"
    _copy_database(source, target)
    target.chmod(0o600)
    return target


def _copy_database(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(target) as target_connection:
            source_connection.backup(target_connection)


def _checkpoint_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def check_consistency(config: DatabaseConfig, *, require_secret: bool = True) -> None:
    if not schema_is_current(config.path):
        raise ValueError("database schema or task protocol is incompatible")
    if require_secret and not config.secret_key_file.is_file():
        raise ValueError("external secret key is missing")
    if require_secret:
        load_cipher(config.secret_key_file)
    with sqlite3.connect(config.path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise ValueError("SQLite integrity check failed")


def _require_installation(config: DatabaseConfig) -> None:
    if not config.path.is_file():
        raise ValueError("installation is not initialized")
    if not config.secret_key_file.is_file():
        raise ValueError("external secret key is missing")
    load_cipher(config.secret_key_file)


def _validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"default timezone is invalid: {value}") from exc


def _validate_username(value: str) -> str:
    username = value.strip()
    if not username:
        raise ValueError("administrator username must not be empty")
    return username


def _remove_sqlite_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)


def _prepare_data_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
