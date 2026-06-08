"""Long-running single-worker execution engine."""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Callable
from pathlib import Path

from weather_morning_report.backups import ensure_scheduled_backups
from weather_morning_report.jobs import (
    ClaimedJob,
    acquire_worker_lease,
    claim_job,
    complete_job,
    enqueue_due_jobs,
    fail_uncertain_deliveries,
    fail_job,
    release_worker_lease,
    renew_worker_lease,
)
from weather_morning_report.database.core import DatabaseConfig
from weather_morning_report.database.operations import check_consistency
from weather_morning_report.v3_service import process_report_job, record_failed_job

LOGGER = logging.getLogger("weather_morning_report.worker")


class WorkerAlreadyRunningError(RuntimeError):
    pass


def serve_worker(config: DatabaseConfig | None = None) -> None:
    database = config or DatabaseConfig.from_env()
    check_consistency(database)
    run_worker(
        database.path,
        lambda job: process_report_job(database, job),
        on_exhausted=lambda job, error: record_failed_job(database, job, error),
    )


def run_worker(
    database_path: Path,
    processor: Callable[[ClaimedJob], str],
    *,
    instance_id: str | None = None,
    once: bool = False,
    poll_seconds: float = 5,
    on_exhausted: Callable[[ClaimedJob, Exception], None] | None = None,
) -> None:
    worker_id = instance_id or secrets.token_urlsafe(12)
    if not acquire_worker_lease(database_path, worker_id):
        raise WorkerAlreadyRunningError("another worker holds the active lease")
    stop_heartbeat = threading.Event()
    lease_lost = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(database_path, worker_id, stop_heartbeat, lease_lost),
        daemon=True,
        name="weather-report-worker-heartbeat",
    )
    heartbeat.start()
    try:
        while True:
            if lease_lost.is_set():
                raise WorkerAlreadyRunningError("worker lease was lost")
            try:
                ensure_scheduled_backups(database_path)
            except Exception:
                LOGGER.exception("scheduled backup maintenance failed")
            fail_uncertain_deliveries(database_path)
            enqueue_due_jobs(database_path)
            job = claim_job(database_path, worker_id)
            if job:
                try:
                    result = processor(job)
                    complete_job(database_path, job.id, worker_id, status=result)
                except Exception as exc:
                    LOGGER.exception("job execution failed", extra={"job_id": job.id})
                    status = fail_job(
                        database_path,
                        job.id,
                        worker_id,
                        error_code=type(exc).__name__,
                        error_message=str(exc),
                    )
                    if status == "failed" and on_exhausted:
                        on_exhausted(job, exc)
            if once:
                return
            time.sleep(poll_seconds)
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=2)
        release_worker_lease(database_path, worker_id)


def _heartbeat_loop(
    database_path: Path,
    worker_id: str,
    stop: threading.Event,
    lease_lost: threading.Event,
) -> None:
    while not stop.wait(30):
        try:
            if not renew_worker_lease(database_path, worker_id):
                lease_lost.set()
                return
        except Exception:
            LOGGER.exception("worker heartbeat failed")
            lease_lost.set()
            return
