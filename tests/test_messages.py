from weather_morning_report.delivery.messages import (
    build_admin_failure_message,
    build_report_message,
)
from test_settings import complete_settings


def test_report_message_is_multipart_alternative() -> None:
    message = build_report_message(
        complete_settings(),
        subject="[带伞] 天气早报",
        text="纯文本报告",
        html="<html><body>HTML 报告</body></html>",
    )

    assert message["To"] == "recipient@example.com"
    assert message["From"] == "sender@example.com"
    assert message.is_multipart()
    assert [part.get_content_type() for part in message.iter_parts()] == [
        "text/plain",
        "text/html",
    ]


def test_admin_failure_message_does_not_target_recipient() -> None:
    message = build_admin_failure_message(complete_settings(), RuntimeError("offline"))

    assert message["To"] == "admin@example.com"
    assert "recipient@example.com" not in str(message)
    assert "offline" in message.get_content()
