from weather_morning_report.providers.wttr import parse_wttr_payload
from weather_morning_report.recommendations import recommend
from weather_morning_report.rendering.html import render_html
from weather_morning_report.rendering.text import render_text
from test_wttr_provider import FETCHED_AT, SHANGHAI, payload


def test_cached_report_clearly_labels_data_time() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )

    text = render_text(snapshot, recommend(snapshot), cached=True)

    assert "实时天气源暂时不可用" in text
    assert "2026-06-06 08:30 CST 的缓存数据" in text


def test_html_report_contains_email_safe_content() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )

    html = render_html(snapshot, recommend(snapshot))

    assert html.startswith("<!doctype html>")
    assert "<meta name=\"viewport\"" in html
    assert "关键时段" in html
    assert "<script" not in html
    assert "http://" not in html
    assert "https://" not in html


def test_reports_use_configured_recipient_name() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    advice = recommend(snapshot)

    assert "小明，早上好。" in render_text(snapshot, advice, recipient_name=" 小明 ")
    assert "小明，早上好。" in render_html(snapshot, advice, recipient_name=" 小明 ")


def test_reports_use_default_greeting_without_recipient_name() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    advice = recommend(snapshot)

    assert "\n早上好。\n" in render_text(snapshot, advice)
    assert "<p>早上好。</p>" in render_html(snapshot, advice)
