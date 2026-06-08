"""SQLite-backed scheduling, queue leases, deduplication, and retries."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from weather_morning_report.database.core import create_sqlite_engine, open_session
from weather_morning_report.database.models import (
    Job,
    Recipient,
    RunHistory,
    Schedule,
    WorkerLease,
    utc_now,
)

WORKER_LEASE_ID = 1
WORKER_LEASE_DURATION = timedelta(seconds=90)
JOB_LEASE_DURATION = timedelta(minutes=5)
RETRY_DELAYS = (
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
    timedelta(minutes=60),
)
RETRY_CUTOFF = timedelta(hours=2)
REPORT_TYPES = {"morning", "midday", "evening"}


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: int
    recipient_id: int
    schedule_id: int | None
    report_type: str
    kind: str
    attempt_count: int
    lease_owner: str
    preview_digest: str | None


@dataclass(frozen=True, slots=True)
class QueueStatus:
    pending: int
    running: int
    retrying: int
    sent: int
    skipped: int
    failed: int
    worker_instance_id: str | None
    worker_heartbeat_at: datetime | None
    worker_active: bool


def queue_status(path: Path, *, now: datetime | None = None) -> QueueStatus:
    current = _utc_naive(now)
    with open_session(path) as session:
        statuses = tuple(session.scalars(select(Job.status)))
        lease = session.get(WorkerLease, WORKER_LEASE_ID)
        counts = {status: statuses.count(status) for status in {
            "pending", "running", "retrying", "sent", "skipped", "failed"
        }}
        counts["running"] += statuses.count("dispatching")
        return QueueStatus(
            **counts,
            worker_instance_id=lease.instance_id if lease else None,
            worker_heartbeat_at=lease.heartbeat_at if lease else None,
            worker_active=bool(lease and lease.expires_at > current),
        )


def acquire_worker_lease(
    path: Path,
    instance_id: str,
    *,
    now: datetime | None = None,
) -> bool:
    current = _utc_naive(now)
    with _immediate_session(path) as session:
        lease = session.get(WorkerLease, WORKER_LEASE_ID)
        if lease and lease.instance_id != instance_id and lease.expires_at > current:
            return False
        if lease is None:
            lease = WorkerLease(
                id=WORKER_LEASE_ID,
                instance_id=instance_id,
                acquired_at=current,
                heartbeat_at=current,
                expires_at=current + WORKER_LEASE_DURATION,
            )
            session.add(lease)
        else:
            if lease.instance_id != instance_id:
                lease.acquired_at = current
            lease.instance_id = instance_id
            lease.heartbeat_at = current
            lease.expires_at = current + WORKER_LEASE_DURATION
        return True


def renew_worker_lease(
    path: Path,
    instance_id: str,
    *,
    now: datetime | None = None,
) -> bool:
    current = _utc_naive(now)
    with _immediate_session(path) as session:
        lease = session.get(WorkerLease, WORKER_LEASE_ID)
        if lease is None or lease.instance_id != instance_id or lease.expires_at <= current:
            return False
        lease.heartbeat_at = current
        lease.expires_at = current + WORKER_LEASE_DURATION
        return True


def release_worker_lease(path: Path, instance_id: str) -> None:
    with _immediate_session(path) as session:
        lease = session.get(WorkerLease, WORKER_LEASE_ID)
        if lease and lease.instance_id == instance_id:
            session.delete(lease)


def enqueue_due_jobs(path: Path, *, now: datetime | None = None) -> int:
    current_aware = _utc_aware(now)
    created = 0
    with _immediate_session(path) as session:
        rows = session.execute(
            select(Schedule, Recipient)
            .join(Recipient, Schedule.recipient_id == Recipient.id)
            .where(
                Schedule.enabled.is_(True),
                Schedule.archived_at.is_(None),
                Recipient.enabled.is_(True),
                Recipient.archived_at.is_(None),
            )
        ).all()
        for schedule, recipient in rows:
            local_now = current_aware.astimezone(ZoneInfo(recipient.timezone))
            if schedule.local_send_time != local_now.strftime("%H:%M"):
                continue
            job = Job(
                recipient_id=recipient.id,
                schedule_id=schedule.id,
                local_report_date=local_now.date(),
                report_type=schedule.report_type,
                kind="automatic",
                status="pending",
                scheduled_at=_utc_naive(current_aware),
                available_at=_utc_naive(current_aware),
            )
            try:
                with session.begin_nested():
                    session.add(job)
                    session.flush()
                created += 1
            except IntegrityError:
                pass
    return created


def enqueue_manual_job(
    path: Path,
    *,
    recipient_id: int,
    report_type: str,
    preview_digest: str | None = None,
    now: datetime | None = None,
) -> Job:
    if report_type not in REPORT_TYPES:
        raise ValueError("report type is invalid")
    current = _utc_naive(now)
    with _immediate_session(path) as session:
        recipient = session.get(Recipient, recipient_id)
        if recipient is None or recipient.archived_at is not None:
            raise ValueError("recipient does not exist or is archived")
        job = Job(
            recipient_id=recipient_id,
            schedule_id=None,
            local_report_date=None,
            report_type=report_type,
            kind="manual",
            status="pending",
            scheduled_at=current,
            available_at=current,
            preview_digest=preview_digest,
        )
        session.add(job)
        session.flush()
        return job


def claim_job(
    path: Path,
    instance_id: str,
    *,
    now: datetime | None = None,
) -> ClaimedJob | None:
    current = _utc_naive(now)
    with _immediate_session(path) as session:
        job = session.scalar(
            select(Job)
            .where(
                Job.available_at <= current,
                or_(
                    Job.status.in_(("pending", "retrying")),
                    (Job.status == "running") & (Job.lease_expires_at <= current),
                ),
            )
            .order_by(Job.available_at, Job.id)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.attempt_count += 1
        job.lease_owner = instance_id
        job.lease_expires_at = current + JOB_LEASE_DURATION
        job.updated_at = current
        return ClaimedJob(
            id=job.id,
            recipient_id=job.recipient_id,
            schedule_id=job.schedule_id,
            report_type=job.report_type,
            kind=job.kind,
            attempt_count=job.attempt_count,
            lease_owner=instance_id,
            preview_digest=job.preview_digest,
        )


def begin_delivery(
    path: Path,
    job_id: int,
    instance_id: str,
    *,
    now: datetime | None = None,
) -> None:
    with _immediate_session(path) as session:
        job = _owned_job(session, job_id, instance_id)
        job.status = "dispatching"
        job.updated_at = _utc_naive(now)


def fail_uncertain_deliveries(path: Path, *, now: datetime | None = None) -> int:
    current = _utc_naive(now)
    with _immediate_session(path) as session:
        jobs = tuple(
            session.scalars(
                select(Job).where(
                    Job.status == "dispatching",
                    Job.lease_expires_at <= current,
                )
            )
        )
        for job in jobs:
            completed_status = session.scalar(
                select(RunHistory.status)
                .where(
                    RunHistory.job_id == job.id,
                    RunHistory.status.in_(("sent", "skipped")),
                )
                .order_by(RunHistory.id.desc())
                .limit(1)
            )
            job.status = completed_status or "failed"
            if completed_status is None:
                job.last_error_code = "delivery_result_unknown"
                job.last_error_message = (
                    "worker stopped after delivery began; automatic resend was suppressed"
                )
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = current
        return len(jobs)


def complete_job(
    path: Path,
    job_id: int,
    instance_id: str,
    *,
    status: str = "sent",
    now: datetime | None = None,
) -> None:
    if status not in {"sent", "skipped"}:
        raise ValueError("completed job status must be sent or skipped")
    with open_session(path) as session:
        job = _owned_job(session, job_id, instance_id, statuses={"running", "dispatching"})
        job.status = status
        job.lease_owner = None
        job.lease_expires_at = None
        job.updated_at = _utc_naive(now)
        session.commit()


def fail_job(
    path: Path,
    job_id: int,
    instance_id: str,
    *,
    error_code: str,
    error_message: str,
    now: datetime | None = None,
) -> str:
    current = _utc_naive(now)
    with open_session(path) as session:
        job = _owned_job(session, job_id, instance_id, statuses={"running", "dispatching"})
        delivery_was_started = job.status == "dispatching"
        retry_index = job.attempt_count - 1
        retry_at = (
            current + RETRY_DELAYS[retry_index]
            if retry_index < len(RETRY_DELAYS)
            else None
        )
        if delivery_was_started:
            job.status = "failed"
            error_code = "delivery_result_unknown"
            error_message = (
                "delivery began but did not complete cleanly; automatic resend was suppressed"
            )
        elif retry_at is not None and retry_at <= job.scheduled_at + RETRY_CUTOFF:
            job.status = "retrying"
            job.available_at = retry_at
        else:
            job.status = "failed"
        job.last_error_code = error_code[:100]
        job.last_error_message = error_message[:1000]
        job.lease_owner = None
        job.lease_expires_at = None
        job.updated_at = current
        session.commit()
        return job.status


def _owned_job(
    session,
    job_id: int,
    instance_id: str,
    *,
    statuses: set[str] | None = None,
) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError("job does not exist")
    if job.status not in (statuses or {"running"}) or job.lease_owner != instance_id:
        raise ValueError("job is not owned by this worker")
    return job


def _utc_naive(value: datetime | None) -> datetime:
    return _utc_aware(value).replace(tzinfo=None)


def _utc_aware(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@contextmanager
def _immediate_session(path: Path) -> Iterator[Session]:
    engine = create_sqlite_engine(path)
    with Session(engine, expire_on_commit=False) as session:
        session.execute(text("BEGIN IMMEDIATE"))
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
