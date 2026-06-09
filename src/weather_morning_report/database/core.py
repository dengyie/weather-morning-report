"""SQLite engine, session, and migration helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

SCHEMA_VERSION = 3
TASK_PROTOCOL_VERSION = 1
APPLICATION_VERSION = "4.0.0-dev"


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    path: Path
    secret_key_file: Path

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        return cls(
            path=Path(os.getenv("WEATHER_REPORT_DB_PATH", "var/weather-report.db")),
            secret_key_file=Path(
                os.getenv("WEATHER_REPORT_SECRET_KEY_FILE", "var/secret.key")
            ),
        )


def create_sqlite_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


@contextmanager
def open_session(path: Path) -> Iterator[Session]:
    engine = create_sqlite_engine(path)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        yield session


def alembic_config(path: Path) -> AlembicConfig:
    config = AlembicConfig()
    migrations = Path(__file__).resolve().parent.parent / "migrations"
    config.set_main_option("script_location", str(migrations))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def upgrade_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(path), "head")


def schema_is_current(path: Path) -> bool:
    if not path.exists():
        return False
    engine = create_sqlite_engine(path)
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        if "app_meta" not in tables:
            return False
        row = connection.execute(
            text(
                "SELECT schema_version, task_protocol_version "
                "FROM app_meta WHERE id = 1"
            )
        ).one_or_none()
    return bool(
        row
        and row.schema_version == SCHEMA_VERSION
        and row.task_protocol_version == TASK_PROTOCOL_VERSION
    )
