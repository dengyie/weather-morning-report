"""Workday and rest-day report period selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True, slots=True)
class ReportPeriod:
    label: str
    start: time
    end: time


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


def schedule_for(report_date: date) -> PeriodSchedule:
    """Return the Phase 1 Monday-Friday or weekend schedule."""

    is_workday = report_date.weekday() < 5
    return PeriodSchedule(
        is_workday=is_workday,
        periods=WORKDAY_PERIODS if is_workday else REST_DAY_PERIODS,
    )
