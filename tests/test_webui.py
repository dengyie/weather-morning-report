import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weather_morning_report.settings import SettingsStore
from weather_morning_report.webui import _settings_from_form, make_handler
from test_settings import complete_settings


def test_form_keeps_existing_password_when_blank() -> None:
    form = {
        "recipient_name": ["Demo"],
        "recipient_email": ["recipient@example.com"],
        "admin_email": ["admin@example.com"],
        "sender_email": ["sender@example.com"],
        "smtp_host": ["smtp.example.com"],
        "smtp_port": ["587"],
        "smtp_username": ["sender@example.com"],
        "smtp_password": [""],
        "smtp_security": ["starttls"],
    }

    settings = _settings_from_form(form, "existing-secret")

    assert settings.smtp_password == "existing-secret"


def test_local_web_ui_saves_settings(tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    token = "test-token"
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, token))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        page = urlopen(f"http://127.0.0.1:{server.server_port}/").read().decode()
        assert "天气早报设置" in page

        settings = complete_settings()
        form = {
            "csrf_token": token,
            "recipient_name": settings.recipient_name,
            "recipient_email": settings.recipient_email,
            "admin_email": settings.admin_email,
            "sender_email": settings.sender_email,
            "smtp_host": settings.smtp_host,
            "smtp_port": str(settings.smtp_port),
            "smtp_username": settings.smtp_username,
            "smtp_password": settings.smtp_password,
            "smtp_security": settings.smtp_security,
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/save",
            data=urlencode(form).encode(),
            method="POST",
        )
        response = urlopen(request).read().decode()

        assert "设置已保存" in response
        assert store.load() == settings
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

