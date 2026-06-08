from datetime import UTC, datetime, timedelta

from weather_morning_report.backups import (
    ensure_scheduled_backups,
    list_backups,
    resolve_backup_path,
)
from weather_morning_report.database.core import DatabaseConfig
from weather_morning_report.database.operations import initialize_installation


def initialized_config(tmp_path) -> DatabaseConfig:
    config = DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )
    return config


def test_scheduled_backups_are_idempotent_per_day_and_week(tmp_path) -> None:
    config = initialized_config(tmp_path)
    now = datetime(2026, 6, 8, 1, 0, tzinfo=UTC)

    first = ensure_scheduled_backups(config.path, now=now)
    second = ensure_scheduled_backups(config.path, now=now + timedelta(hours=2))

    assert {backup.kind for backup in first} == {"daily", "weekly"}
    assert second == ()
    assert len(list_backups(config.path)) == 2
    for backup in first:
        assert resolve_backup_path(config.path, backup.id).is_file()


def test_scheduled_backup_retention_keeps_seven_daily_and_four_weekly(tmp_path) -> None:
    config = initialized_config(tmp_path)
    start = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)

    for week in range(6):
        for day in range(7):
            ensure_scheduled_backups(
                config.path,
                now=start + timedelta(weeks=week, days=day),
            )

    backups = list_backups(config.path)
    daily = [backup for backup in backups if backup.kind == "daily"]
    weekly = [backup for backup in backups if backup.kind == "weekly"]
    assert len(daily) == 7
    assert len(weekly) == 4
    assert len(tuple((config.path.parent / "backups").glob("*.db"))) == 11


def test_database_backup_does_not_include_external_secret_key(tmp_path) -> None:
    config = initialized_config(tmp_path)
    secret = config.secret_key_file.read_bytes()

    backup = ensure_scheduled_backups(
        config.path,
        now=datetime(2026, 6, 8, tzinfo=UTC),
    )[0]

    assert secret not in resolve_backup_path(config.path, backup.id).read_bytes()
