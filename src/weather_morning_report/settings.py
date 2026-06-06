"""Local delivery settings and secure-on-disk persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from email.utils import parseaddr
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RecipientSettings:
    name: str
    email: str
    location_name: str = ""
    location_query: str = ""

    def validate(self) -> None:
        if not _is_email(self.email):
            raise ValueError(f"Recipient email is invalid: {self.email}")
        if bool(self.location_name) != bool(self.location_query):
            raise ValueError(
                "Recipient location name and query must both be set or both be empty"
            )


@dataclass(frozen=True, slots=True)
class DeliverySettings:
    recipient_name: str = ""
    recipient_email: str = ""
    admin_email: str = ""
    sender_email: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_security: str = "starttls"
    recipients: tuple[RecipientSettings, ...] = ()

    def validate(self, *, require_complete: bool = False) -> None:
        if not 1 <= self.smtp_port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535")
        if self.smtp_security not in {"starttls", "ssl", "plain"}:
            raise ValueError("SMTP security must be starttls, ssl, or plain")
        for label, value in (
            ("Recipient email", self.recipient_email),
            ("Administrator email", self.admin_email),
            ("Sender email", self.sender_email),
        ):
            if value and not _is_email(value):
                raise ValueError(f"{label} is invalid")
        for recipient in self.recipients:
            recipient.validate()
        recipient_emails = [recipient.email.lower() for recipient in self.recipients]
        if len(recipient_emails) != len(set(recipient_emails)):
            raise ValueError("Recipient emails must be unique")
        if require_complete:
            missing = [
                label
                for label, value in (
                    ("administrator email", self.admin_email),
                    ("sender email", self.sender_email),
                    ("SMTP host", self.smtp_host),
                )
                if not value
            ]
            if not self.recipients and not self.recipient_email:
                missing.insert(0, "recipient email or recipients")
            if missing:
                raise ValueError("Missing required settings: " + ", ".join(missing))


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DeliverySettings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return DeliverySettings()
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Settings file is invalid: {exc}") from exc
        return _from_mapping(data)

    def save(self, settings: DeliverySettings) -> None:
        settings.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        os.replace(temporary, self.path)
        self.path.chmod(0o600)


def load_delivery_settings(path: Path) -> DeliverySettings:
    stored = SettingsStore(path).load()
    values = asdict(stored)
    environment = {
        "recipient_name": "RECIPIENT_NAME",
        "recipient_email": "RECIPIENT_EMAIL",
        "admin_email": "ADMIN_EMAIL",
        "sender_email": "SENDER_EMAIL",
        "smtp_host": "SMTP_HOST",
        "smtp_port": "SMTP_PORT",
        "smtp_username": "SMTP_USERNAME",
        "smtp_password": "SMTP_PASSWORD",
        "smtp_security": "SMTP_SECURITY",
    }
    for field_name, environment_name in environment.items():
        if environment_name in os.environ:
            values[field_name] = os.environ[environment_name]
    if "RECIPIENTS_JSON" in os.environ:
        recipients_json = os.environ["RECIPIENTS_JSON"].strip()
        if recipients_json:
            try:
                values["recipients"] = json.loads(recipients_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"RECIPIENTS_JSON is invalid: {exc}") from exc
    return _from_mapping(values)


def load_recipient_name(path: Path) -> str:
    if "RECIPIENT_NAME" in os.environ:
        return os.environ["RECIPIENT_NAME"].strip()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ""
        recipient_name = data.get("recipient_name", "")
        return recipient_name.strip() if isinstance(recipient_name, str) else ""
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ""


def load_preview_recipient(path: Path) -> RecipientSettings | None:
    try:
        settings = load_delivery_settings(path)
    except (OSError, TypeError, ValueError):
        return None
    if settings.recipients:
        return settings.recipients[0]
    if settings.recipient_email:
        return RecipientSettings(settings.recipient_name, settings.recipient_email)
    return None


def _from_mapping(data: dict[str, Any]) -> DeliverySettings:
    recipients_data = data.get("recipients", [])
    if not isinstance(recipients_data, (list, tuple)):
        raise ValueError("Recipients must be a list")
    settings = DeliverySettings(
        recipient_name=str(data.get("recipient_name", "")).strip(),
        recipient_email=str(data.get("recipient_email", "")).strip(),
        admin_email=str(data.get("admin_email", "")).strip(),
        sender_email=str(data.get("sender_email", "")).strip(),
        smtp_host=str(data.get("smtp_host", "")).strip(),
        smtp_port=int(data.get("smtp_port", 587)),
        smtp_username=str(data.get("smtp_username", "")).strip(),
        smtp_password=str(data.get("smtp_password", "")),
        smtp_security=str(data.get("smtp_security", "starttls")).strip().lower(),
        recipients=tuple(_recipient_from_mapping(item) for item in recipients_data),
    )
    settings.validate()
    return settings


def _recipient_from_mapping(data: Any) -> RecipientSettings:
    if not isinstance(data, dict):
        raise ValueError("Each recipient must be an object")
    return RecipientSettings(
        name=str(data.get("name", "")).strip(),
        email=str(data.get("email", "")).strip(),
        location_name=str(data.get("location_name", "")).strip(),
        location_query=str(data.get("location_query", "")).strip(),
    )


def _is_email(value: str) -> bool:
    _, address = parseaddr(value)
    local, separator, domain = address.rpartition("@")
    return bool(separator and local and "." in domain and not domain.startswith("."))
