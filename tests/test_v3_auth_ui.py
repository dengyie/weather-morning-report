from fastapi.testclient import TestClient
import re
from datetime import timedelta
from sqlalchemy import select

from weather_morning_report.auth import (
    authenticated_admin,
    login,
    logout_all,
)
from weather_morning_report.backups import ensure_scheduled_backups
from weather_morning_report.configuration import load_configuration
from weather_morning_report.database.core import DatabaseConfig, open_session
from weather_morning_report.database.models import AuditEvent, Schedule, SessionRecord
from weather_morning_report.database.operations import initialize_installation
from weather_morning_report.ui import create_app
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.database.models import Job, utc_now


def initialized_config(tmp_path) -> DatabaseConfig:
    config = DatabaseConfig(tmp_path / "weather-report.db", tmp_path / "secret.key")
    initialize_installation(
        config,
        username="admin",
        password="correct horse battery",
        default_timezone="Asia/Shanghai",
    )
    return config


def authenticated_client(config: DatabaseConfig) -> tuple[TestClient, str]:
    client = TestClient(create_app(config), follow_redirects=False)
    client.post(
        "/login",
        data={"username": "admin", "password": "correct horse battery"},
    )
    page = client.get("/configuration")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    return client, csrf


def test_login_creates_persistent_hashed_session(tmp_path) -> None:
    config = initialized_config(tmp_path)

    result = login(
        config.path,
        username="admin",
        password="correct horse battery",
        source="127.0.0.1",
    )

    assert result.token
    assert authenticated_admin(config.path, result.token).username == "admin"
    with open_session(config.path) as session:
        record = session.scalar(select(SessionRecord))
        assert record is not None
        assert record.id != result.token


def test_five_failures_lock_login_without_revealing_username(tmp_path) -> None:
    config = initialized_config(tmp_path)

    results = [
        login(
            config.path,
            username="unknown",
            password="incorrect password",
            source="127.0.0.1",
        )
        for _ in range(5)
    ]
    blocked = login(
        config.path,
        username="admin",
        password="correct horse battery",
        source="127.0.0.1",
    )

    assert results[-1].locked is True
    assert blocked.locked is True
    assert blocked.token is None


def test_logout_all_revokes_every_session_and_audits(tmp_path) -> None:
    config = initialized_config(tmp_path)
    token = login(
        config.path,
        username="admin",
        password="correct horse battery",
        source="127.0.0.1",
    ).token

    logout_all(config.path, "admin")

    assert authenticated_admin(config.path, token) is None
    with open_session(config.path) as session:
        events = session.scalars(select(AuditEvent.event_type)).all()
        assert "logout_all" in events


def test_health_endpoints_are_minimal_and_openapi_is_disabled(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client = TestClient(create_app(config))

    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get("/openapi.json").status_code == 404


def test_health_ready_hides_failure_details(tmp_path) -> None:
    config = DatabaseConfig(tmp_path / "missing.db", tmp_path / "missing.key")
    response = TestClient(create_app(config)).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_ui_login_cookie_and_protected_dashboard(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client = TestClient(create_app(config), follow_redirects=False)

    assert client.get("/").status_code == 303
    response = client.post(
        "/login",
        data={"username": "admin", "password": "correct horse battery"},
    )

    assert response.status_code == 303
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert client.get("/", follow_redirects=True).status_code == 200


def test_ui_failed_login_uses_generic_error(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client = TestClient(create_app(config))

    response = client.post(
        "/login",
        data={"username": "missing", "password": "incorrect password"},
    )

    assert response.status_code == 401
    assert "用户名或密码不正确" in response.text


def test_configuration_page_requires_authentication(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client = TestClient(create_app(config), follow_redirects=False)

    assert client.get("/configuration").status_code == 303


def test_backup_download_requires_authentication_and_returns_database(tmp_path) -> None:
    config = initialized_config(tmp_path)
    backup = ensure_scheduled_backups(config.path)[0]
    anonymous = TestClient(create_app(config), follow_redirects=False)
    client, _ = authenticated_client(config)

    assert anonymous.get(f"/backups/{backup.id}/download").status_code == 303
    response = client.get(f"/backups/{backup.id}/download")
    assert response.status_code == 200
    assert response.content.startswith(b"SQLite format 3")
    assert backup.path in response.headers["content-disposition"]
    assert client.get("/backups/9999/download").status_code == 404


def test_configuration_page_creates_recipient_with_csrf(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)

    response = client.post(
        "/configuration/recipients",
        data={
            "csrf_token": csrf,
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )

    assert response.status_code == 303
    assert "alice@example.com" in client.get("/configuration").text
    with open_session(config.path) as session:
        schedule = session.scalar(select(Schedule).where(Schedule.recipient_id == 1))
        assert schedule is not None
        assert schedule.local_send_time == "08:30"
        assert schedule.report_type == "morning"
        assert schedule.send_policy == "always"
        assert schedule.enabled is True


def test_configuration_page_saves_new_user_defaults(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)

    response = client.post(
        "/configuration/new-user-defaults",
        data={
            "csrf_token": csrf,
            "location_name": "Beijing",
            "location_query": "Beijing",
            "timezone": "Asia/Shanghai",
            "language": "en",
            "local_send_time": "12:15",
            "report_type": "midday",
            "send_policy": "changes_only",
        },
    )

    assert response.status_code == 303
    defaults = load_configuration(config.path).new_user_defaults
    assert defaults.location_name == "Beijing"
    assert defaults.language == "en"
    assert defaults.local_send_time == "12:15"
    assert defaults.report_type == "midday"
    assert defaults.send_policy == "changes_only"
    assert defaults.schedule_enabled is False


def test_editing_recipient_does_not_create_another_default_schedule(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    data = {
        "csrf_token": csrf,
        "name": "Alice",
        "email": "alice@example.com",
        "location_name": "Shanghai",
        "location_query": "Shanghai",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "enabled": "on",
    }
    client.post("/configuration/recipients", data=data)
    client.post(
        "/configuration/recipients",
        data={**data, "recipient_id": "1", "name": "Alice Updated"},
    )

    with open_session(config.path) as session:
        schedules = session.scalars(
            select(Schedule).where(Schedule.recipient_id == 1)
        ).all()
        assert len(schedules) == 1


def test_configuration_write_rejects_invalid_csrf(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, _ = authenticated_client(config)

    response = client.post(
        "/configuration/recipients",
        data={
            "csrf_token": "wrong",
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_configuration_ui_manages_schedule_and_global_settings(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    client.post(
        "/configuration/recipients",
        data={
            "csrf_token": csrf,
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )
    client.post(
        "/configuration/schedules",
        data={
            "csrf_token": csrf,
            "recipient_id": "1",
            "local_send_time": "08:30",
            "report_type": "morning",
            "send_policy": "always",
            "enabled": "on",
        },
    )
    client.post(
        "/configuration/smtp",
        data={
            "csrf_token": csrf,
            "host": "smtp.example.com",
            "port": "587",
            "username": "sender@example.com",
            "password": "smtp-secret",
            "security": "starttls",
            "sender_email": "sender@example.com",
        },
    )
    client.post(
        "/configuration/providers/1",
        data={
            "csrf_token": csrf,
            "priority": "5",
            "enabled": "on",
            "credentials": "provider-secret",
        },
    )
    client.post(
        "/configuration/branding",
        data={
            "csrf_token": csrf,
            "report_title": "Daily Weather",
            "footer_text": "Take care",
            "accent_color": "#abcdef",
            "greeting_visible": "on",
            "data_source_visible": "on",
        },
    )
    client.post(
        "/configuration/notifications",
        data={
            "csrf_token": csrf,
            "admin_email": "admin@example.com",
            "webhook_url": "https://example.com/hook",
            "webhook_enabled": "on",
            "retention_days": "90",
            "alert_cooldown_minutes": "60",
            "secret_key_backup_confirmed": "on",
        },
    )

    page = client.get("/configuration")
    assert page.status_code == 200
    assert "08:30" in page.text
    assert "smtp.example.com" in page.text
    assert "smtp-secret" not in page.text
    assert "provider-secret" not in page.text
    assert "Daily Weather" in page.text


def test_configuration_ui_archives_and_restores_items(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    client.post(
        "/configuration/recipients",
        data={
            "csrf_token": csrf,
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )
    client.post(
        "/configuration/schedules",
        data={
            "csrf_token": csrf,
            "recipient_id": "1",
            "local_send_time": "08:30",
            "report_type": "morning",
            "send_policy": "always",
            "enabled": "on",
        },
    )

    assert client.post(
        "/configuration/schedules/1/archive", data={"csrf_token": csrf}
    ).status_code == 303
    assert client.post(
        "/configuration/schedules/1/restore", data={"csrf_token": csrf}
    ).status_code == 303
    assert client.post(
        "/configuration/recipients/1/archive", data={"csrf_token": csrf}
    ).status_code == 303
    assert "Alice" in client.get("/configuration?archived=1").text
    assert client.post(
        "/configuration/recipients/1/restore", data={"csrf_token": csrf}
    ).status_code == 303


def test_configuration_ui_returns_validation_error(tmp_path) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)

    response = client.post(
        "/configuration/branding",
        data={
            "csrf_token": csrf,
            "report_title": "Bad",
            "footer_text": "",
            "accent_color": "red",
        },
    )

    assert response.status_code == 400
    assert "accent color" in response.text


def test_manual_send_requires_preview_confirmation(tmp_path, monkeypatch) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    client.post(
        "/configuration/recipients",
        data={
            "csrf_token": csrf,
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )
    monkeypatch.setattr(
        "weather_morning_report.ui.preview_recipient_report",
        lambda config, **kwargs: ("Subject", "Preview body", "<p>Preview</p>"),
    )

    direct = client.post(
        "/manual/enqueue",
        data={
            "csrf_token": csrf,
            "confirmation_token": "not-previewed",
            "recipient_id": "1",
            "report_type": "morning",
        },
    )
    preview = client.post(
        "/manual/preview",
        data={"csrf_token": csrf, "recipient_id": "1", "report_type": "morning"},
    )
    confirmation = re.search(
        r'name="confirmation_token" value="([^"]+)"', preview.text
    ).group(1)
    preview_digest = re.search(
        r'name="preview_digest" value="([^"]+)"', preview.text
    ).group(1)
    enqueue = client.post(
        "/manual/enqueue",
        data={
            "csrf_token": csrf,
            "confirmation_token": confirmation,
            "preview_digest": preview_digest,
            "recipient_id": "1",
            "report_type": "morning",
        },
    )
    replay = client.post(
        "/manual/enqueue",
        data={
            "csrf_token": csrf,
            "confirmation_token": confirmation,
            "preview_digest": preview_digest,
            "recipient_id": "1",
            "report_type": "morning",
        },
    )

    assert direct.headers["location"] == "/"
    assert "Preview body" in preview.text
    assert enqueue.headers["location"] == "/"
    assert replay.headers["location"] == "/"


def test_manual_confirmation_expires_and_detects_configuration_change(
    tmp_path, monkeypatch
) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    client.post(
        "/configuration/recipients",
        data={
            "csrf_token": csrf,
            "name": "Alice",
            "email": "alice@example.com",
            "location_name": "Shanghai",
            "location_query": "Shanghai",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "enabled": "on",
        },
    )
    monkeypatch.setattr(
        "weather_morning_report.ui.preview_recipient_report",
        lambda config, **kwargs: ("Subject", "Preview body", "<p>Preview</p>"),
    )
    preview = client.post(
        "/manual/preview",
        data={"csrf_token": csrf, "recipient_id": "1", "report_type": "morning"},
    )
    confirmation = re.search(
        r'name="confirmation_token" value="([^"]+)"', preview.text
    ).group(1)
    digest = re.search(r'name="preview_digest" value="([^"]+)"', preview.text).group(1)
    monkeypatch.setattr(
        "weather_morning_report.ui.utc_now",
        lambda: utc_now() + timedelta(minutes=6),
    )

    expired = client.post(
        "/manual/enqueue",
        data={
            "csrf_token": csrf,
            "confirmation_token": confirmation,
            "preview_digest": digest,
            "recipient_id": "1",
            "report_type": "morning",
        },
    )

    assert expired.headers["location"] == "/"
    with open_session(config.path) as session:
        assert session.scalar(select(Job)) is None


def test_manual_preview_handles_provider_failure(tmp_path, monkeypatch) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    monkeypatch.setattr(
        "weather_morning_report.ui.preview_recipient_report",
        lambda config, **kwargs: (_ for _ in ()).throw(ProviderError("offline")),
    )

    response = client.post(
        "/manual/preview",
        data={"csrf_token": csrf, "recipient_id": "1", "report_type": "morning"},
    )

    assert response.status_code == 400
    assert "offline" in response.text


def test_manual_confirmation_rejects_changed_recipient(tmp_path, monkeypatch) -> None:
    config = initialized_config(tmp_path)
    client, csrf = authenticated_client(config)
    recipient_data = {
        "csrf_token": csrf,
        "name": "Alice",
        "email": "alice@example.com",
        "location_name": "Shanghai",
        "location_query": "Shanghai",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "enabled": "on",
    }
    client.post("/configuration/recipients", data=recipient_data)
    monkeypatch.setattr(
        "weather_morning_report.ui.preview_recipient_report",
        lambda config, **kwargs: ("Subject", "Preview body", "<p>Preview</p>"),
    )
    preview = client.post(
        "/manual/preview",
        data={"csrf_token": csrf, "recipient_id": "1", "report_type": "morning"},
    )
    confirmation = re.search(
        r'name="confirmation_token" value="([^"]+)"', preview.text
    ).group(1)
    digest = re.search(r'name="preview_digest" value="([^"]+)"', preview.text).group(1)
    client.post(
        "/configuration/recipients",
        data={**recipient_data, "recipient_id": "1", "email": "new@example.com"},
    )

    response = client.post(
        "/manual/enqueue",
        data={
            "csrf_token": csrf,
            "confirmation_token": confirmation,
            "preview_digest": digest,
            "recipient_id": "1",
            "report_type": "morning",
        },
    )

    assert response.headers["location"] == "/"
    with open_session(config.path) as session:
        assert session.scalar(select(Job)) is None
