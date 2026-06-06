"""SMTP connectivity checks."""

from __future__ import annotations

import smtplib
import ssl

from weather_morning_report.settings import DeliverySettings


def test_smtp_connection(settings: DeliverySettings, timeout: float = 10) -> str:
    settings.validate()
    if not settings.smtp_host:
        raise ValueError("SMTP host is required")
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
    return "SMTP connection and authentication succeeded."
