import stat

import pytest

from weather_morning_report.settings import (
    DeliverySettings,
    SettingsStore,
    load_delivery_settings,
)


def complete_settings(**overrides) -> DeliverySettings:
    values = {
        "recipient_name": "Demo",
        "recipient_email": "recipient@example.com",
        "admin_email": "admin@example.com",
        "sender_email": "sender@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "sender@example.com",
        "smtp_password": "secret",
        "smtp_security": "starttls",
    }
    values.update(overrides)
    return DeliverySettings(**values)


def test_settings_round_trip_and_file_permissions(tmp_path) -> None:
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = complete_settings()

    store.save(settings)

    assert store.load() == settings
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_environment_overrides_local_settings(tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    SettingsStore(path).save(complete_settings(smtp_host="stored.example.com"))
    monkeypatch.setenv("SMTP_HOST", "env.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")

    settings = load_delivery_settings(path)

    assert settings.smtp_host == "env.example.com"
    assert settings.smtp_port == 465


def test_complete_settings_requires_admin_and_smtp() -> None:
    with pytest.raises(ValueError, match="administrator email.*SMTP host"):
        DeliverySettings(
            recipient_email="recipient@example.com",
            sender_email="sender@example.com",
        ).validate(require_complete=True)


def test_settings_reject_invalid_email() -> None:
    with pytest.raises(ValueError, match="Recipient email is invalid"):
        complete_settings(recipient_email="not-an-email").validate()

