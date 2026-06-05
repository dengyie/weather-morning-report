"""Small Phase 1 recommendation engine used by the demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from weather_morning_report.models import HourlyForecast, WeatherCondition, WeatherSnapshot

RAIN = {
    WeatherCondition.DRIZZLE,
    WeatherCondition.RAIN,
    WeatherCondition.HEAVY_RAIN,
    WeatherCondition.THUNDERSTORM,
}


@dataclass(frozen=True, slots=True)
class PeriodAdvice:
    label: str
    summary: str


@dataclass(frozen=True, slots=True)
class ReportAdvice:
    subject: str
    focus: str
    umbrella: str
    sunscreen: str
    clothing: str
    closing: str
    periods: tuple[PeriodAdvice, ...]


def recommend(snapshot: WeatherSnapshot) -> ReportAdvice:
    morning = _between(snapshot, time(7), time(10))
    midday = _between(snapshot, time(11), time(15))
    evening = _between(snapshot, time(17), time(20))
    commute = morning + evening
    all_points = morning + midday + evening

    commute_rain = _rain_risk(commute)
    midday_rain = _rain_risk(midday)
    thunder = any(point.condition == WeatherCondition.THUNDERSTORM for point in all_points)
    uv = max(
        [snapshot.daily.uv_index or 0]
        + [point.uv_index or 0 for point in midday]
    )
    max_feels = max(
        [snapshot.current.feels_like_c]
        + [point.feels_like_c for point in all_points]
    )

    if thunder:
        subject = "[雷雨风险，注意安全] 天气早报"
        focus = "今天有雷雨风险，外出留意天气变化"
    elif commute_rain >= 45:
        subject = "[通勤有雨，记得带伞] 天气早报"
        focus = "通勤时段可能有雨"
    elif max_feels >= 32:
        subject = "[今天闷热，穿轻薄些] 天气早报"
        focus = "今天体感偏热，注意通风补水"
    elif uv >= 6:
        subject = "[紫外线很强，注意防晒] 天气早报"
        focus = "午间紫外线较强"
    elif midday_rain >= 20:
        subject = "[午间可能有雨] 天气早报"
        focus = "午间可能有短时降雨"
    else:
        subject = "[天气舒服，适合出门] 天气早报"
        focus = "今天整体天气平稳"

    umbrella = _umbrella(commute_rain, midday_rain, thunder)
    sunscreen = _sunscreen(uv)
    clothing = _clothing(max_feels, all_points, max(commute_rain, midday_rain))
    closing = _closing(thunder, max(commute_rain, midday_rain), max_feels, uv)
    periods = (
        PeriodAdvice("早通勤", _period_summary(morning)),
        PeriodAdvice("午间", _period_summary(midday)),
        PeriodAdvice("晚通勤", _period_summary(evening)),
    )
    return ReportAdvice(subject, focus, umbrella, sunscreen, clothing, closing, periods)


def _between(
    snapshot: WeatherSnapshot,
    start: time,
    end: time,
) -> tuple[HourlyForecast, ...]:
    return tuple(
        point
        for point in snapshot.hourly
        if start <= point.forecast_at.timetz().replace(tzinfo=None) < end
    )


def _rain_risk(points: tuple[HourlyForecast, ...]) -> int:
    if not points:
        return 0
    explicit_rain = any(point.condition in RAIN for point in points)
    probability = max(point.precipitation_probability_percent or 0 for point in points)
    return max(probability, 45 if explicit_rain else 0)


def _umbrella(commute_rain: int, midday_rain: int, thunder: bool) -> str:
    if thunder or commute_rain >= 45:
        return "建议带一把轻便伞"
    if midday_rain >= 20:
        return "午间可能有雨，可随手带伞"
    return "今天通常不用带伞"


def _sunscreen(uv: float) -> str:
    if uv >= 8:
        return f"UV {uv:g}，强烈建议防晒、遮阳，长时间户外注意补涂"
    if uv >= 6:
        return f"UV {uv:g}，建议认真防晒并尽量走阴凉处"
    if uv >= 3:
        return f"UV {uv:g}，建议做好日常防晒"
    return f"UV {uv:g}，无需特别加强防晒"


def _clothing(
    max_feels: float,
    points: tuple[HourlyForecast, ...],
    rain_risk: int,
) -> str:
    if max_feels >= 32:
        text = "短袖或透气薄上衣搭配轻薄下装，注意通风散热"
    elif max_feels >= 27:
        text = "短袖或薄衬衫搭配轻薄下装"
    elif max_feels >= 22:
        text = "短袖或薄衬衫即可"
    else:
        text = "建议带一件轻薄外套"
    if any((point.humidity_percent or 0) >= 80 for point in points):
        text += "；优先选择透气、易干的面料"
    if rain_risk >= 45:
        text += "；避免容易吸水的鞋"
    return text


def _period_summary(points: tuple[HourlyForecast, ...]) -> str:
    if not points:
        return "暂无可靠数据"
    representative = max(
        points,
        key=lambda point: point.precipitation_probability_percent or 0,
    )
    rain = max(point.precipitation_probability_percent or 0 for point in points)
    feels = round(sum(point.feels_like_c for point in points) / len(points))
    return f"{representative.description}，降雨概率最高 {rain}% ，体感约 {feels}°C"


def _closing(thunder: bool, rain: int, max_feels: float, uv: float) -> str:
    if thunder:
        return "雷雨时尽量减少户外停留，路上注意安全。"
    if rain >= 45:
        return "今天可能下雨，回家路上慢一点。"
    if max_feels >= 32:
        return "今天会有些热，记得及时喝水。"
    if uv >= 6:
        return "午间阳光强，出门记得做好防晒。"
    return "今天天气还算舒服，祝你一天顺利。"

