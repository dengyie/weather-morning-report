from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from weather_morning_report.configuration import save_recipient, save_schedule
from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import Backup, Job, RunHistory, WorkerLease
from weather_morning_report.database.operations import initialize_installation
from weather_morning_report.jobs import (
    acquire_worker_lease,
    claim_job,
    complete_job,
    begin_delivery,
    enqueue_due_jobs,
    enqueue_manual_job,
    fail_job,
    fail_uncertain_deliveries,
    queue_status,
    release_worker_lease,
    renew_worker_lease,
)
from weather_morning_report.worker import WorkerAlreadyRunningError, run_worker


NOW = datetime(2026, 6, 8, 0, 30, tzinfo=UTC)


def initialized_config(tmp_path) -> DatabaseConfig:
    config = DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )
    return config


def scheduled_recipient(config: DatabaseConfig, *, policy: str = "always"):
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
    schedule = save_schedule(
        config.path,
        actor="admin",
        schedule_id=None,
        recipient_id=recipient.id,
        local_send_time="08:30",
        report_type="morning",
        send_policy=policy,
        enabled=True,
    )
    return recipient, schedule


def test_scheduler_enqueues_due_job_once_per_local_date(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, schedule = scheduled_recipient(config)

    assert enqueue_due_jobs(config.path, now=NOW) == 1
    assert enqueue_due_jobs(config.path, now=NOW + timedelta(seconds=30)) == 0

    with open_session(config.path) as session:
        job = session.scalar(select(Job))
        assert job.recipient_id == recipient.id
        assert job.schedule_id == schedule.id
        assert job.local_report_date.isoformat() == "2026-06-08"


def test_scheduler_does_not_backfill_missed_minute(tmp_path) -> None:
    config = initialized_config(tmp_path)
    scheduled_recipient(config)

    assert enqueue_due_jobs(config.path, now=NOW + timedelta(minutes=2)) == 0


def test_single_worker_lease_and_expired_takeover(tmp_path) -> None:
    config = initialized_config(tmp_path)

    assert acquire_worker_lease(config.path, "worker-a", now=NOW)
    assert not acquire_worker_lease(config.path, "worker-b", now=NOW)
    assert renew_worker_lease(config.path, "worker-a", now=NOW + timedelta(seconds=30))
    assert acquire_worker_lease(config.path, "worker-b", now=NOW + timedelta(minutes=3))
    assert not renew_worker_lease(config.path, "worker-a", now=NOW + timedelta(minutes=3))
    release_worker_lease(config.path, "worker-b")
    with open_session(config.path) as session:
        assert session.get(WorkerLease, 1) is None


def test_claim_recovers_expired_job_lease_and_complete_requires_owner(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    job = enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    first = claim_job(config.path, "worker-a", now=NOW)

    with pytest.raises(ValueError, match="not owned"):
        complete_job(config.path, job.id, "worker-b", now=NOW)
    recovered = claim_job(config.path, "worker-b", now=NOW + timedelta(minutes=6))
    complete_job(config.path, recovered.id, "worker-b", status="sent", now=NOW)

    with open_session(config.path) as session:
        assert session.get(Job, first.id).status == "sent"
        assert session.get(Job, first.id).attempt_count == 2


def test_retry_delays_then_exhausts_after_two_hours(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    job = enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    current = NOW
    expected_delays = [5, 15, 30, 60]
    for delay in expected_delays:
        claimed = claim_job(config.path, "worker", now=current)
        assert fail_job(
            config.path,
            claimed.id,
            "worker",
            error_code="offline",
            error_message="provider unavailable",
            now=current,
        ) == "retrying"
        current += timedelta(minutes=delay)
    claimed = claim_job(config.path, "worker", now=current)
    assert fail_job(
        config.path,
        claimed.id,
        "worker",
        error_code="offline",
        error_message="provider unavailable",
        now=current,
    ) == "failed"
    with open_session(config.path) as session:
        stored = session.get(Job, job.id)
        assert stored.attempt_count == 5
        assert stored.last_error_code == "offline"


def test_worker_once_processes_job_and_releases_lease(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=datetime.now(UTC),
    )

    run_worker(config.path, lambda job: "skipped", instance_id="worker", once=True)

    with open_session(config.path) as session:
        assert session.scalar(select(Job)).status == "skipped"
        assert session.scalar(select(Backup)) is not None
        assert session.get(WorkerLease, 1) is None


def test_worker_continues_when_scheduled_backup_fails(tmp_path, monkeypatch) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "weather_morning_report.worker.ensure_scheduled_backups",
        lambda path: (_ for _ in ()).throw(OSError("disk full")),
    )

    run_worker(config.path, lambda job: "skipped", instance_id="worker", once=True)

    with open_session(config.path) as session:
        assert session.scalar(select(Job)).status == "skipped"


def test_uncertain_delivery_is_failed_without_resend(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    job = enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    claimed = claim_job(config.path, "worker-a", now=NOW)
    begin_delivery(config.path, claimed.id, "worker-a", now=NOW)

    assert fail_uncertain_deliveries(config.path, now=NOW + timedelta(minutes=6)) == 1
    assert claim_job(config.path, "worker-b", now=NOW + timedelta(minutes=6)) is None
    with open_session(config.path) as session:
        stored = session.get(Job, job.id)
        assert stored.status == "failed"
        assert stored.last_error_code == "delivery_result_unknown"


def test_uncertain_delivery_recovers_completed_run_without_resend(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    job = enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    claimed = claim_job(config.path, "worker-a", now=NOW)
    begin_delivery(config.path, claimed.id, "worker-a", now=NOW)
    with open_session(config.path) as session:
        session.add(
            RunHistory(
                job_id=job.id,
                recipient_id=recipient.id,
                status="sent",
                report_type="morning",
                recipient_name_snapshot="Alice",
                masked_email_snapshot="a***@example.com",
            )
        )
        session.commit()

    assert fail_uncertain_deliveries(config.path, now=NOW + timedelta(minutes=6)) == 1
    assert claim_job(config.path, "worker-b", now=NOW + timedelta(minutes=6)) is None
    with open_session(config.path) as session:
        assert session.get(Job, job.id).status == "sent"


def test_worker_refuses_when_active_lease_exists(tmp_path) -> None:
    config = initialized_config(tmp_path)
    assert acquire_worker_lease(config.path, "worker-a")

    with pytest.raises(WorkerAlreadyRunningError, match="another worker"):
        run_worker(config.path, lambda job: "sent", instance_id="worker-b", once=True)


def test_worker_calls_exhausted_handler_after_final_failure(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    job = enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    with open_session(config.path) as session:
        stored = session.get(Job, job.id)
        stored.attempt_count = 4
        stored.available_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()
    exhausted = []

    run_worker(
        config.path,
        lambda job: (_ for _ in ()).throw(RuntimeError("offline")),
        instance_id="worker",
        once=True,
        on_exhausted=lambda job, error: exhausted.append((job.id, str(error))),
    )

    assert exhausted == [(job.id, "offline")]


def test_queue_status_reports_jobs_and_worker_heartbeat(tmp_path) -> None:
    config = initialized_config(tmp_path)
    recipient, _ = scheduled_recipient(config)
    enqueue_manual_job(
        config.path,
        recipient_id=recipient.id,
        report_type="morning",
        now=NOW,
    )
    acquire_worker_lease(config.path, "worker", now=NOW)

    status = queue_status(config.path, now=NOW)

    assert status.pending == 1
    assert status.worker_active is True
    assert status.worker_instance_id == "worker"
