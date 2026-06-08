"""Workday and rest-day report period selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True, slots=True)
class ReportPeriod:
    label: str
    start: time
    end: time
    day_offset: int = 0


@dataclass(frozen=True, slots=True)
class PeriodSchedule:
    is_workday: bool
    periods: tuple[ReportPeriod, ...]


WORKDAY_PERIODS = (
    ReportPeriod("早通勤", time(7), time(10)),
    ReportPeriod("午间", time(11), time(14)),
    ReportPeriod("晚通勤", time(17), time(20)),
)

REST_DAY_PERIODS = (
    ReportPeriod("上午", time(8), time(11)),
    ReportPeriod("下午", time(12), time(17)),
    ReportPeriod("晚上", time(18), time(22)),
)


MIDDAY_PERIODS = (
    ReportPeriod("下午", time(12), time(17)),
    ReportPeriod("晚上", time(17), time(22)),
)

EVENING_PERIODS = (
    ReportPeriod("今晚", time(17), time(23, 59, 59)),
    ReportPeriod("次日早晨", time(6), time(10), day_offset=1),
)


def schedule_for(report_date: date, report_type: str = "morning") -> PeriodSchedule:
    """Return periods for a morning, midday, or evening report."""

    is_workday = report_date.weekday() < 5
    if report_type == "midday":
        periods = MIDDAY_PERIODS
    elif report_type == "evening":
        periods = EVENING_PERIODS
    elif report_type == "morning":
        periods = WORKDAY_PERIODS if is_workday else REST_DAY_PERIODS
    else:
        raise ValueError(f"unsupported report type: {report_type}")
    return PeriodSchedule(
        is_workday=is_workday,
        periods=periods,
    )


def period_bounds(report_date: date, period: ReportPeriod) -> tuple[datetime, datetime]:
    target_date = report_date + timedelta(days=period.day_offset)
    return datetime.combine(target_date, period.start), datetime.combine(target_date, period.end)
