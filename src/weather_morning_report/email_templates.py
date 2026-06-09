"""Email presentation template choices."""

from __future__ import annotations

EMAIL_TEMPLATE_OPTIONS = (
    ("1", "暖调风格"),
    ("2", "行动风格"),
    ("3", "玻璃渐变"),
    ("4", "极简风格"),
    ("5", "仪表风格"),
)
DEFAULT_EMAIL_TEMPLATE = "1"
EMAIL_TEMPLATES = frozenset(value for value, _label in EMAIL_TEMPLATE_OPTIONS)


def email_template_label(value: str) -> str:
    labels = dict(EMAIL_TEMPLATE_OPTIONS)
    return labels.get(value, labels[DEFAULT_EMAIL_TEMPLATE])


def normalize_email_template(value: str) -> str:
    return value if value in EMAIL_TEMPLATES else DEFAULT_EMAIL_TEMPLATE
