import pytest

from weather_morning_report.delivery import smtp
from weather_morning_report.settings import DeliverySettings
from test_settings import complete_settings


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.calls = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, message):
        self.calls.append(("send_message", message))


def test_starttls_connection_logs_in(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtp.smtplib, "SMTP", FakeSMTP)

    message = smtp.test_smtp_connection(complete_settings())

    assert message.endswith("succeeded.")
    assert FakeSMTP.instances[0].calls == [
        "ehlo",
        "starttls",
        "ehlo",
        ("login", "sender@example.com", "secret"),
    ]


def test_ssl_connection_uses_smtp_ssl(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtp.smtplib, "SMTP_SSL", FakeSMTP)

    smtp.test_smtp_connection(complete_settings(smtp_security="ssl", smtp_port=465))

    assert FakeSMTP.instances[0].port == 465
    assert "starttls" not in FakeSMTP.instances[0].calls


def test_connection_test_only_requires_smtp_settings() -> None:
    with pytest.raises(ValueError, match="SMTP host is required"):
        smtp.test_smtp_connection(DeliverySettings())


def test_send_message_delivers_email(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtp.smtplib, "SMTP", FakeSMTP)
    message = smtp.EmailMessage()
    message["Subject"] = "Test"
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message.set_content("Hello")

    smtp.send_message(complete_settings(), message)

    assert FakeSMTP.instances[0].calls[-1] == ("send_message", message)


def test_send_test_email_targets_administrator(monkeypatch) -> None:
    sent = []
    monkeypatch.setattr(smtp, "send_message", lambda settings, message: sent.append(message))

    result = smtp.send_test_email(complete_settings())

    assert result == "Test email sent to admin@example.com."
    assert sent[0]["To"] == "admin@example.com"
    assert "正式天气早报尚未触发" in sent[0].get_content()
