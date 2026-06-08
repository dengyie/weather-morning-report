"""Scheduled SQLite backups and retention."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from weather_morning_report.database.core import open_session
from weather_morning_report.database.models import Backup
from weather_morning_report.database.operations import backup_database

DAILY_RETENTION = 7
WEEKLY_RETENTION = 4


def ensure_scheduled_backups(
    database_path: Path,
    *,
    now: datetime | None = None,
) -> tuple[Backup, ...]:
    current = _naive_utc(now)
    created: list[Backup] = []
    backup_directory = database_path.parent / "backups"
    with open_session(database_path) as session:
        existing = tuple(session.scalars(select(Backup)))
        due_kinds = ["daily"] if not _has_daily(existing, current) else []
        if not _has_weekly(existing, current):
            due_kinds.append("weekly")

    for kind in due_kinds:
        path = backup_database(database_path, backup_directory, kind, now=current)
        with open_session(database_path) as session:
            record = Backup(
                path=path.name,
                kind=kind,
                created_at=current,
                size_bytes=path.stat().st_size,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            created.append(record)

    prune_backups(database_path)
    return tuple(created)


def list_backups(database_path: Path) -> tuple[Backup, ...]:
    with open_session(database_path) as session:
        return tuple(session.scalars(select(Backup).order_by(Backup.created_at.desc())))


def resolve_backup_path(database_path: Path, backup_id: int) -> Path:
    with open_session(database_path) as session:
        backup = session.get(Backup, backup_id)
        if backup is None:
            raise ValueError("backup does not exist")
        filename = Path(backup.path)
    if filename.name != backup.path:
        raise ValueError("backup path is invalid")
    path = database_path.parent / "backups" / filename
    if not path.is_file():
        raise ValueError("backup file is missing")
    return path


def prune_backups(
    database_path: Path,
    *,
    daily_retention: int = DAILY_RETENTION,
    weekly_retention: int = WEEKLY_RETENTION,
) -> None:
    limits = {"daily": daily_retention, "weekly": weekly_retention}
    with open_session(database_path) as session:
        records = tuple(
            session.scalars(
                select(Backup).order_by(Backup.kind, Backup.created_at.desc())
            )
        )
        seen: dict[str, int] = {}
        for backup in records:
            if backup.kind not in limits:
                continue
            seen[backup.kind] = seen.get(backup.kind, 0) + 1
            if seen[backup.kind] <= limits[backup.kind]:
                continue
            path = database_path.parent / "backups" / Path(backup.path).name
            path.unlink(missing_ok=True)
            session.delete(backup)
        session.commit()


def _has_daily(backups: tuple[Backup, ...], now: datetime) -> bool:
    return any(
        backup.kind == "daily" and backup.created_at.date() == now.date()
        for backup in backups
    )


def _has_weekly(backups: tuple[Backup, ...], now: datetime) -> bool:
    iso_year, iso_week, _ = now.isocalendar()
    return any(
        backup.kind == "weekly"
        and backup.created_at.isocalendar()[:2] == (iso_year, iso_week)
        for backup in backups
    )


def _naive_utc(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is not None:
        current = current.astimezone(UTC).replace(tzinfo=None)
    return current
