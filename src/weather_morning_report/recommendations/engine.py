"""Small Phase 1 recommendation engine used by the demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from weather_morning_report.models import HourlyForecast, WeatherCondition, WeatherSnapshot
from weather_morning_report.recommendations.periods import schedule_for

RAIN = {
    WeatherCondition.DRIZZLE,
    WeatherCondition.RAIN,
    WeatherCondition.HEAVY_RAIN,
    WeatherCondition.THUNDERSTORM,
}

THUNDER_PROBABILITY_THRESHOLD = 40
MEANINGFUL_PRECIPITATION_MM = 0.5
STRONG_WIND_KPH = 40
DANGEROUS_HEAT_C = 38


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


def recommend(
    snapshot: WeatherSnapshot,
    *,
    report_date: date | None = None,
) -> ReportAdvice:
    schedule = schedule_for(report_date or snapshot.daily.forecast_date)
    period_points = tuple(
        _between(snapshot, period.start, period.end) for period in schedule.periods
    )
    morning, midday, evening = period_points
    primary_outing = morning + evening if schedule.is_workday else sum(period_points, ())
    all_points = sum(period_points, ())

    primary_rain = _rain_risk(primary_outing)
    midday_rain = _rain_risk(midday)
    thunder = any(
        point.condition == WeatherCondition.THUNDERSTORM
        or (point.thunder_probability_percent or 0) >= THUNDER_PROBABILITY_THRESHOLD
        for point in all_points
    )
    heavy_rain = any(point.condition == WeatherCondition.HEAVY_RAIN for point in all_points)
    strongest_wind = max(
        [snapshot.current.wind_speed_kph or 0]
        + [point.wind_speed_kph or 0 for point in all_points]
    )
    strong_wind = strongest_wind >= STRONG_WIND_KPH
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
    elif heavy_rain:
        subject = "[有较强降雨，注意出行] 天气早报"
        focus = "今天有较强降雨，外出注意积水和路况"
    elif strong_wind:
        subject = "[今天风大，注意安全] 天气早报"
        focus = "今天风力较强，外出注意安全"
    elif max_feels >= DANGEROUS_HEAT_C:
        subject = "[高温风险，注意防暑] 天气早报"
        focus = "今天体感炎热，注意防暑降温"
    elif primary_rain >= 45:
        subject = (
            "[通勤有雨，记得带伞] 天气早报"
            if schedule.is_workday
            else "[出行有雨，记得带伞] 天气早报"
        )
        focus = "通勤时段可能有雨" if schedule.is_workday else "今天外出可能遇到雨"
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

    umbrella = _umbrella(primary_rain, midday_rain, thunder)
    sunscreen = _sunscreen(uv)
    rain_risk = max(primary_rain, midday_rain)
    clothing = _clothing(max_feels, all_points, rain_risk, strong_wind)
    closing = _closing(
        thunder,
        heavy_rain,
        strong_wind,
        rain_risk,
        max_feels,
        uv,
    )
    periods = tuple(
        PeriodAdvice(period.label, _period_summary(points))
        for period, points in zip(schedule.periods, period_points, strict=True)
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
    meaningful_precipitation = any(
        (point.precipitation_mm or 0) >= MEANINGFUL_PRECIPITATION_MM for point in points
    )
    probability = max(point.precipitation_probability_percent or 0 for point in points)
    return max(probability, 45 if explicit_rain or meaningful_precipitation else 0)


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
    strong_wind: bool,
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
    if strong_wind:
        text += "；可带防风外层并收好易被吹动的物品"
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


def _closing(
    thunder: bool,
    heavy_rain: bool,
    strong_wind: bool,
    rain: int,
    max_feels: float,
    uv: float,
) -> str:
    if thunder:
        return "雷雨时尽量减少户外停留，路上注意安全。"
    if heavy_rain:
        return "今天降雨较强，外出留意积水和路况。"
    if strong_wind:
        return "今天风力较强，外出注意高空坠物和随身物品。"
    if max_feels >= DANGEROUS_HEAT_C:
        return "今天体感炎热，尽量避开长时间户外活动并及时补水。"
    if rain >= 45:
        return "今天可能下雨，回家路上慢一点。"
    if max_feels >= 32:
        return "今天会有些热，记得及时喝水。"
    if uv >= 6:
        return "午间阳光强，出门记得做好防晒。"
    return "今天天气还算舒服，祝你一天顺利。"
