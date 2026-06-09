from dataclasses import replace

import pytest

from weather_morning_report.models import WeatherCondition
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
    assert 'data-email-template="1"' in html


def test_html_report_supports_all_email_templates() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    advice = recommend(snapshot)

    for template in ("1", "2", "3", "4", "5"):
        html = render_html(snapshot, advice, email_template=template)
        assert f'data-email-template="{template}"' in html
        assert "天气早报" in html
        assert "<script" not in html


def test_html_report_uses_modern_visual_enhancements() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )

    html = render_html(snapshot, recommend(snapshot), email_template="3")

    assert "--accent" in html
    assert "linear-gradient" in html
    assert "box-shadow" in html
    assert "backdrop-filter" in html


def test_html_weather_visual_changes_with_current_condition() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    clear_snapshot = replace(
        snapshot,
        current=replace(snapshot.current, condition=WeatherCondition.CLEAR),
    )
    rain_snapshot = replace(
        snapshot,
        current=replace(snapshot.current, condition=WeatherCondition.RAIN),
    )

    clear_html = render_html(clear_snapshot, recommend(clear_snapshot))
    rain_html = render_html(rain_snapshot, recommend(rain_snapshot))

    assert 'data-weather-condition="clear"' in clear_html
    assert 'data-weather-condition="rain"' in rain_html
    assert 'class="weather-visual weather-visual-warm weather-clear"' in clear_html
    assert 'class="weather-visual weather-visual-warm weather-rain"' in rain_html
    assert "weather-scene-clear" in clear_html
    assert "weather-scene-rain" in rain_html
    assert 'r="42"' in clear_html
    assert "M61 129l-11 25" in rain_html
    assert "M61 129l-11 25" not in clear_html
    assert clear_html != rain_html


def test_weather_color_theme_changes_with_current_condition() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    rain_snapshot = replace(
        snapshot,
        current=replace(snapshot.current, condition=WeatherCondition.RAIN),
    )

    html = render_html(rain_snapshot, recommend(rain_snapshot), email_template="1")

    assert '<body class="weather-rain">' in html
    assert "body.weather-rain" in html
    assert "#e8f4f9" in html
    assert "body.weather-clear" in html
    assert "#f7efe4" in html
    assert "body { margin: 0; background: var(--weather-page-bg);" in html


@pytest.mark.parametrize(
    "condition",
    [
        WeatherCondition.PARTLY_CLOUDY,
        WeatherCondition.CLOUDY,
        WeatherCondition.FOG,
        WeatherCondition.DRIZZLE,
        WeatherCondition.RAIN,
        WeatherCondition.HEAVY_RAIN,
        WeatherCondition.THUNDERSTORM,
        WeatherCondition.SNOW,
        WeatherCondition.SLEET,
        WeatherCondition.UNKNOWN,
    ],
)
def test_non_clear_weather_themes_do_not_use_clear_page_colors(
    condition: WeatherCondition,
) -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    themed_snapshot = replace(
        snapshot,
        current=replace(snapshot.current, condition=condition),
    )

    html = render_html(themed_snapshot, recommend(themed_snapshot), email_template="1")
    condition_class = condition.value.replace("_", "-")
    body_start = html.index(f"body.weather-{condition_class}")
    body_end = html.index("    }", body_start)
    weather_block = html[body_start:body_end]

    assert "#f7efe4" not in weather_block
    assert "#ecd9c0" not in weather_block
    assert "#fff8ec" not in weather_block
    assert "#f3d1a6" not in weather_block


def test_all_html_templates_include_weather_visual() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    rain_snapshot = replace(
        snapshot,
        current=replace(snapshot.current, condition=WeatherCondition.RAIN),
    )
    advice = recommend(rain_snapshot)

    for template in ("1", "2", "3", "4", "5"):
        html = render_html(rain_snapshot, advice, email_template=template)
        assert f'data-email-template="{template}"' in html
        assert 'data-weather-condition="rain"' in html
        assert '<body class="weather-rain">' in html
        assert "body { margin: 0; background: var(--weather-page-bg);" in html
        assert "weather-visual" in html
        assert "weather-scene-rain" in html
        assert "M61 129l-11 25" in html


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


def test_english_evening_report_uses_english_labels_and_greeting() -> None:
    snapshot = parse_wttr_payload(
        payload(midday_rain=0),
        location_name="Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    advice = recommend(snapshot, language="en")

    text = render_text(
        snapshot,
        advice,
        recipient_name="Alice",
        language="en",
        report_type="evening",
    )
    html = render_html(snapshot, advice, recipient_name="Alice", language="en")

    assert "Good evening, Alice." in text
    assert "Umbrella:" in text
    assert "带伞" not in text
    assert '<html lang="en">' in html


def test_rendering_can_hide_greeting_and_source_and_show_footer() -> None:
    snapshot = parse_wttr_payload(
        payload(),
        location_name="Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    advice = recommend(snapshot)

    text = render_text(
        snapshot,
        advice,
        greeting_visible=False,
        footer_text="Custom footer",
        data_source_visible=False,
    )
    html = render_html(
        snapshot,
        advice,
        greeting_visible=False,
        footer_text="Custom footer",
        accent_color="#abcdef",
        data_source_visible=False,
    )

    assert "早上好" not in text
    assert "数据来源" not in text
    assert "Custom footer" in text
    assert "早上好" not in html
    assert "数据来源" not in html
    assert "#abcdef" in html
