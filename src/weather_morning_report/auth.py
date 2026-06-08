"""Persistent single-administrator authentication for the v3 UI."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select

from weather_morning_report.database.core import open_session
from weather_morning_report.database.models import (
    Admin,
    AuditEvent,
    LoginAttempt,
    SessionRecord,
    utc_now,
)
from weather_morning_report.database.security import hash_password, verify_password

SESSION_LIFETIME = timedelta(hours=12)
LOCKOUT_WINDOW = timedelta(minutes=15)
LOCKOUT_FAILURES = 5
_DUMMY_HASH = hash_password("not-a-real-admin-password")


@dataclass(frozen=True, slots=True)
class LoginResult:
    token: str | None
    locked: bool


def login(
    database_path: Path,
    *,
    username: str,
    password: str,
    source: str,
) -> LoginResult:
    now = utc_now()
    source_hash = _source_hash(source)
    with open_session(database_path) as session:
        recent_failures = session.scalars(
            select(LoginAttempt)
            .where(
                LoginAttempt.source_hash == source_hash,
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.attempted_at >= now - LOCKOUT_WINDOW,
            )
            .order_by(LoginAttempt.attempted_at.desc())
        ).all()
        if len(recent_failures) >= LOCKOUT_FAILURES:
            session.add(
                AuditEvent(
                    event_type="login_blocked",
                    actor="anonymous",
                    details_json='{"reason":"lockout"}',
                )
            )
            session.commit()
            return LoginResult(None, locked=True)

        admin = session.scalar(select(Admin))
        valid = verify_password(
            admin.password_hash if admin else _DUMMY_HASH,
            password,
        ) and bool(admin and secrets.compare_digest(admin.username, username.strip()))
        session.add(
            LoginAttempt(
                attempted_at=now,
                succeeded=valid,
                source_hash=source_hash,
            )
        )
        if not valid or admin is None:
            session.add(AuditEvent(event_type="login_failed", actor="anonymous"))
            session.commit()
            return LoginResult(
                None,
                locked=len(recent_failures) + 1 >= LOCKOUT_FAILURES,
            )

        session.execute(
            delete(LoginAttempt).where(LoginAttempt.source_hash == source_hash)
        )
        token = secrets.token_urlsafe(32)
        session.add(
            SessionRecord(
                id=_token_hash(token),
                admin_id=admin.id,
                created_at=now,
                expires_at=now + SESSION_LIFETIME,
            )
        )
        session.add(AuditEvent(event_type="login_succeeded", actor=admin.username))
        session.commit()
        return LoginResult(token, locked=False)


def authenticated_admin(database_path: Path, token: str | None) -> Admin | None:
    if not token:
        return None
    now = utc_now()
    with open_session(database_path) as session:
        record = session.get(SessionRecord, _token_hash(token))
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            return None
        return session.get(Admin, record.admin_id)


def logout(database_path: Path, token: str | None) -> None:
    if not token:
        return
    with open_session(database_path) as session:
        record = session.get(SessionRecord, _token_hash(token))
        if record is not None and record.revoked_at is None:
            record.revoked_at = utc_now()
            session.add(AuditEvent(event_type="logout", actor="administrator"))
            session.commit()


def logout_all(database_path: Path, actor: str) -> None:
    with open_session(database_path) as session:
        session.execute(delete(SessionRecord))
        session.add(AuditEvent(event_type="logout_all", actor=actor))
        session.commit()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
