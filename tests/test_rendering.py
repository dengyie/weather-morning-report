from weather_morning_report.providers.wttr import parse_wttr_payload
from weather_morning_report.recommendations import recommend
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
