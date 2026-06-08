from dataclasses import replace
from datetime import date, datetime

from weather_morning_report.models import WeatherCondition
from weather_morning_report.providers.wttr import parse_wttr_payload
from weather_morning_report.recommendations import recommend
from test_wttr_provider import FETCHED_AT, SHANGHAI, payload


def advice_for(**kwargs):
    return recommend(snapshot_for(**kwargs), report_date=date(2026, 6, 8))


def snapshot_for(**kwargs):
    return parse_wttr_payload(
        payload(**kwargs),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )


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


def test_rest_day_uses_outing_periods_and_rain_subject() -> None:
    snapshot = snapshot_for(midday_rain=70, uv=2)

    advice = recommend(snapshot, report_date=date(2026, 6, 6))

    assert advice.subject == "[出行有雨，记得带伞] 天气早报"
    assert advice.umbrella == "建议带一把轻便伞"
    assert [period.label for period in advice.periods] == ["上午", "下午", "晚上"]


def test_thunder_probability_triggers_risk_first_subject() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(
        replace(point, thunder_probability_percent=60)
        if point.forecast_at.hour == 18
        else point
        for point in snapshot.hourly
    )

    advice = recommend(replace(snapshot, hourly=hourly), report_date=date(2026, 6, 8))

    assert advice.subject == "[雷雨风险，注意安全] 天气早报"
    assert "雷雨时尽量减少户外停留" in advice.closing


def test_meaningful_commute_precipitation_triggers_umbrella() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(
        replace(
            point,
            precipitation_probability_percent=10,
            precipitation_mm=0.8,
            condition=WeatherCondition.CLOUDY,
        )
        if point.forecast_at.hour == 9
        else point
        for point in snapshot.hourly
    )

    advice = recommend(replace(snapshot, hourly=hourly), report_date=date(2026, 6, 8))

    assert advice.subject == "[通勤有雨，记得带伞] 天气早报"
    assert advice.umbrella == "建议带一把轻便伞"


def test_heavy_rain_uses_risk_first_subject() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(
        replace(point, condition=WeatherCondition.HEAVY_RAIN)
        if point.forecast_at.hour == 12
        else point
        for point in snapshot.hourly
    )

    advice = recommend(replace(snapshot, hourly=hourly), report_date=date(2026, 6, 8))

    assert advice.subject == "[有较强降雨，注意出行] 天气早报"
    assert "积水和路况" in advice.closing


def test_strong_wind_and_cooling_adds_practical_advice() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(
        replace(point, wind_speed_kph=45, feels_like_c=20)
        for point in snapshot.hourly
    )
    current = replace(snapshot.current, feels_like_c=20, wind_speed_kph=45)

    advice = recommend(
        replace(snapshot, current=current, hourly=hourly),
        report_date=date(2026, 6, 8),
    )

    assert advice.subject == "[今天风大，注意安全] 天气早报"
    assert "防风外层" in advice.clothing
    assert "高空坠物" in advice.closing


def test_dangerous_heat_has_risk_priority_over_uv() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=10)
    hourly = tuple(replace(point, feels_like_c=39) for point in snapshot.hourly)

    advice = recommend(replace(snapshot, hourly=hourly), report_date=date(2026, 6, 8))

    assert advice.subject == "[高温风险，注意防暑] 天气早报"
    assert "避开长时间户外活动" in advice.closing


def test_warm_high_humidity_recommends_quick_drying_fabric() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(replace(point, humidity_percent=90) for point in snapshot.hourly)

    advice = recommend(replace(snapshot, hourly=hourly), report_date=date(2026, 6, 8))

    assert "透气、易干的面料" in advice.clothing


def test_comfortable_day_uses_calm_subject_and_closing() -> None:
    snapshot = snapshot_for(midday_rain=0, uv=2)
    hourly = tuple(replace(point, feels_like_c=25) for point in snapshot.hourly)
    current = replace(snapshot.current, feels_like_c=25)

    advice = recommend(
        replace(snapshot, current=current, hourly=hourly),
        report_date=date(2026, 6, 8),
    )

    assert advice.subject == "[天气舒服，适合出门] 天气早报"
    assert advice.closing == "今天天气还算舒服，祝你一天顺利。"


def test_midday_report_omits_expired_points() -> None:
    snapshot = snapshot_for(midday_rain=70, evening_rain=60, uv=2)

    advice = recommend(
        snapshot,
        report_date=snapshot.daily.forecast_date,
        report_type="midday",
        send_at=datetime(2026, 6, 6, 13, tzinfo=SHANGHAI),
    )

    assert [period.label for period in advice.periods] == ["下午", "晚上"]
    assert advice.periods[0].summary == "暂无可靠数据"
    assert "降雨概率最高 60%" in advice.periods[1].summary


def test_evening_report_states_next_day_unavailable() -> None:
    snapshot = snapshot_for(midday_rain=0, evening_rain=60, uv=2)

    advice = recommend(
        snapshot,
        report_date=snapshot.daily.forecast_date,
        report_type="evening",
        send_at=datetime(2026, 6, 6, 17, tzinfo=SHANGHAI),
    )

    assert [period.label for period in advice.periods] == ["今晚", "次日早晨"]
    assert advice.periods[1].summary == "暂无可靠数据"


def test_action_signals_use_threshold_levels() -> None:
    advice = advice_for(morning_rain=60, uv=10)

    assert advice.signals.umbrella_level == 2
    assert advice.signals.sunscreen_level == 3
    assert advice.signals.target_precipitation_level == 2


def test_english_recommendations_do_not_use_chinese_action_text() -> None:
    snapshot = snapshot_for(morning_rain=60, uv=10)

    advice = recommend(snapshot, report_date=date(2026, 6, 8), language="en")

    assert advice.subject == "[Rain likely, carry an umbrella] Weather report"
    assert "Carry a lightweight umbrella" == advice.umbrella
    assert [period.label for period in advice.periods] == [
        "Morning commute",
        "Midday",
        "Evening commute",
    ]
