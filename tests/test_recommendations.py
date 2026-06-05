from weather_morning_report.providers.wttr import parse_wttr_payload
from weather_morning_report.recommendations import recommend
from test_wttr_provider import FETCHED_AT, SHANGHAI, payload


def advice_for(**kwargs):
    snapshot = parse_wttr_payload(
        payload(**kwargs),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )
    return recommend(snapshot)


def test_midday_rain_uses_soft_umbrella_reminder() -> None:
    advice = advice_for(midday_rain=70)

    assert advice.subject == "[紫外线很强，注意防晒] 天气早报"
    assert advice.umbrella == "午间可能有雨，可随手带伞"


def test_commute_rain_has_higher_subject_priority_than_uv() -> None:
    advice = advice_for(morning_rain=60, uv=10)

    assert advice.subject == "[通勤有雨，记得带伞] 天气早报"
    assert advice.umbrella == "建议带一把轻便伞"


def test_strong_uv_recommendation_is_explicit() -> None:
    advice = advice_for(midday_rain=0, uv=10)

    assert "强烈建议防晒" in advice.sunscreen
