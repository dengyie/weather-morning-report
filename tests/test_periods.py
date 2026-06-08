from datetime import date

from weather_morning_report.recommendations.periods import schedule_for


def test_weekday_uses_commute_periods() -> None:
    schedule = schedule_for(date(2026, 6, 8))

    assert schedule.is_workday is True
    assert [period.label for period in schedule.periods] == ["早通勤", "午间", "晚通勤"]
    assert [(period.start.hour, period.end.hour) for period in schedule.periods] == [
        (7, 10),
        (11, 14),
        (17, 20),
    ]


def test_weekend_uses_rest_day_periods() -> None:
    schedule = schedule_for(date(2026, 6, 6))

    assert schedule.is_workday is False
    assert [period.label for period in schedule.periods] == ["上午", "下午", "晚上"]
    assert [(period.start.hour, period.end.hour) for period in schedule.periods] == [
        (8, 11),
        (12, 17),
        (18, 22),
    ]


def test_midday_and_evening_report_periods() -> None:
    midday = schedule_for(date(2026, 6, 8), "midday")
    evening = schedule_for(date(2026, 6, 8), "evening")

    assert [period.label for period in midday.periods] == ["下午", "晚上"]
    assert [period.label for period in evening.periods] == ["今晚", "次日早晨"]
    assert evening.periods[1].day_offset == 1
