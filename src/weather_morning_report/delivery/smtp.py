"""SMTP connectivity checks."""

from __future__ import annotations

import smtplib
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from email.message import EmailMessage

from weather_morning_report.settings import DeliverySettings


def send_message(
    settings: DeliverySettings,
    message: EmailMessage,
    timeout: float = 20,
) -> None:
    settings.validate()
    if not settings.smtp_host:
        raise ValueError("SMTP host is required")
    with _smtp_client(settings, timeout) as client:
        client.send_message(message)


def test_smtp_connection(settings: DeliverySettings, timeout: float = 10) -> str:
    settings.validate()
    if not settings.smtp_host:
        raise ValueError("SMTP host is required")
    with _smtp_client(settings, timeout):
        pass
    return "SMTP connection and authentication succeeded."


@contextmanager
def _smtp_client(
    settings: DeliverySettings,
    timeout: float,
) -> Iterator[smtplib.SMTP]:
    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=timeout,
            context=context,
        )
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
    with client:
        client.ehlo()
        if settings.smtp_security == "starttls":
            client.starttls(context=context)
            client.ehlo()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        yield client


def send_test_email(settings: DeliverySettings) -> str:
    settings.validate(require_complete=True)
    message = EmailMessage()
    message["Subject"] = "[测试成功] 天气早报邮件配置"
    message["From"] = settings.sender_email
    message["To"] = settings.admin_email
    message.set_content(
        "天气早报 SMTP 配置测试成功。\n\n"
        "这封邮件由本地设置页面发送，正式天气早报尚未触发。"
    )
    send_message(settings, message)
    return f"Test email sent to {settings.admin_email}."
