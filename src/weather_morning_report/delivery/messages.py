"""Multipart weather report and administrator notification messages."""

from __future__ import annotations

from email.message import EmailMessage

from weather_morning_report.settings import DeliverySettings, RecipientSettings


def build_report_message(
    settings: DeliverySettings,
    *,
    subject: str,
    text: str,
    html: str,
    recipient: RecipientSettings | None = None,
) -> EmailMessage:
    settings.validate(require_complete=True)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender_email
    message["To"] = recipient.email if recipient else settings.recipient_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def build_admin_failure_message(
    settings: DeliverySettings,
    error: Exception,
) -> EmailMessage:
    settings.validate(require_complete=True)
    message = EmailMessage()
    message["Subject"] = "[天气早报失败] 无法获取可用天气数据"
    message["From"] = settings.sender_email
    message["To"] = settings.admin_email
    message.set_content(
        "天气早报未发送给收件人。\n\n"
        "实时天气源不可用，并且没有可用的近期缓存。\n"
        f"错误：{error}\n"
    )
    return message
