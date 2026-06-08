"""Small Phase 1 recommendation engine used by the demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from weather_morning_report.models import HourlyForecast, WeatherCondition, WeatherSnapshot
from weather_morning_report.recommendations.periods import period_bounds, schedule_for

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
    signals: ActionSignals


@dataclass(frozen=True, slots=True)
class ActionSignals:
    highest_risk_level: int
    umbrella_level: int
    sunscreen_level: int
    clothing_level: int
    target_precipitation_level: int
    thunderstorm: bool
    strong_wind: bool
    dangerous_heat: bool


def recommend(
    snapshot: WeatherSnapshot,
    *,
    report_date: date | None = None,
    report_type: str = "morning",
    send_at: datetime | None = None,
    language: str = "zh-CN",
) -> ReportAdvice:
    if language not in {"zh-CN", "en"}:
        raise ValueError(f"unsupported report language: {language}")
    report_date = report_date or snapshot.daily.forecast_date
    schedule = schedule_for(report_date, report_type)
    period_points = tuple(
        _period_points(snapshot, report_date, period, send_at) for period in schedule.periods
    )
    all_points = sum(period_points, ())
    if report_type == "morning" and schedule.is_workday and len(period_points) == 3:
        primary_outing = period_points[0] + period_points[2]
        midday = period_points[1]
    else:
        primary_outing = all_points
        midday = tuple(
            point for point in all_points if 11 <= point.forecast_at.hour < 15
        )

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
        PeriodAdvice(_period_label(period.label, language), _period_summary(points, language))
        for period, points in zip(schedule.periods, period_points, strict=True)
    )
    if language == "en":
        subject, focus = _english_subject_focus(
            thunder, heavy_rain, strong_wind, max_feels, primary_rain, uv, midday_rain
        )
        umbrella = _umbrella_en(primary_rain, midday_rain, thunder)
        sunscreen = _sunscreen_en(uv)
        clothing = _clothing_en(max_feels, all_points, rain_risk, strong_wind)
        closing = _closing_en(thunder, heavy_rain, strong_wind, rain_risk, max_feels, uv)
    signals = ActionSignals(
        highest_risk_level=_risk_level(thunder, heavy_rain, strong_wind, max_feels),
        umbrella_level=_umbrella_level(primary_rain, midday_rain, thunder),
        sunscreen_level=_sunscreen_level(uv),
        clothing_level=_clothing_level(max_feels),
        target_precipitation_level=_precipitation_level(rain_risk),
        thunderstorm=thunder,
        strong_wind=strong_wind,
        dangerous_heat=max_feels >= DANGEROUS_HEAT_C,
    )
    return ReportAdvice(subject, focus, umbrella, sunscreen, clothing, closing, periods, signals)


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


def _period_points(snapshot, report_date, period, send_at):
    if send_at is None and period.day_offset == 0:
        return _between(snapshot, period.start, period.end)
    start, end = period_bounds(report_date, period)
    points = tuple(
        point
        for point in snapshot.hourly
        if start <= point.forecast_at.replace(tzinfo=None) < end
    )
    if send_at is None:
        return points
    return tuple(point for point in points if point.forecast_at >= send_at)


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


def _period_summary(points: tuple[HourlyForecast, ...], language: str = "zh-CN") -> str:
    if not points:
        return "No reliable forecast data" if language == "en" else "暂无可靠数据"
    representative = max(
        points,
        key=lambda point: point.precipitation_probability_percent or 0,
    )
    rain = max(point.precipitation_probability_percent or 0 for point in points)
    feels = round(sum(point.feels_like_c for point in points) / len(points))
    if language == "en":
        return f"{representative.description}; rain up to {rain}%; feels like about {feels}°C"
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


def _risk_level(thunder: bool, heavy_rain: bool, strong_wind: bool, max_feels: float) -> int:
    if thunder or heavy_rain:
        return 3
    if strong_wind or max_feels >= DANGEROUS_HEAT_C:
        return 2
    return 0


def _umbrella_level(primary_rain: int, midday_rain: int, thunder: bool) -> int:
    if thunder or primary_rain >= 45:
        return 2
    if midday_rain >= 20:
        return 1
    return 0


def _sunscreen_level(uv: float) -> int:
    if uv >= 8:
        return 3
    if uv >= 6:
        return 2
    if uv >= 3:
        return 1
    return 0


def _clothing_level(max_feels: float) -> int:
    if max_feels >= 32:
        return 3
    if max_feels >= 27:
        return 2
    if max_feels >= 22:
        return 1
    return 0


def _precipitation_level(rain: int) -> int:
    if rain >= 45:
        return 2
    if rain >= 20:
        return 1
    return 0


def _period_label(label: str, language: str) -> str:
    if language != "en":
        return label
    return {
        "早通勤": "Morning commute",
        "午间": "Midday",
        "晚通勤": "Evening commute",
        "上午": "Morning",
        "下午": "Afternoon",
        "晚上": "Evening",
        "今晚": "Tonight",
        "次日早晨": "Next morning",
    }[label]


def _english_subject_focus(thunder, heavy_rain, strong_wind, max_feels, primary_rain, uv, midday_rain):
    if thunder:
        return "[Thunderstorm risk] Weather report", "Thunderstorms are possible; watch conditions when outside"
    if heavy_rain:
        return "[Heavy rain risk] Weather report", "Heavy rain may affect travel today"
    if strong_wind:
        return "[Strong winds today] Weather report", "Strong winds may affect outdoor activity"
    if max_feels >= DANGEROUS_HEAT_C:
        return "[Dangerous heat] Weather report", "It will feel dangerously hot today"
    if primary_rain >= 45:
        return "[Rain likely, carry an umbrella] Weather report", "Rain is likely during your main outing periods"
    if max_feels >= 32:
        return "[Hot today, dress lightly] Weather report", "It will feel hot today; stay ventilated and hydrated"
    if uv >= 6:
        return "[Strong UV, use sun protection] Weather report", "Midday UV will be strong"
    if midday_rain >= 20:
        return "[Possible midday rain] Weather report", "A brief midday shower is possible"
    return "[Comfortable weather] Weather report", "Conditions should remain generally comfortable"


def _umbrella_en(primary_rain: int, midday_rain: int, thunder: bool) -> str:
    if thunder or primary_rain >= 45:
        return "Carry a lightweight umbrella"
    if midday_rain >= 20:
        return "A midday shower is possible; consider a small umbrella"
    return "An umbrella is usually unnecessary today"


def _sunscreen_en(uv: float) -> str:
    if uv >= 8:
        return f"UV {uv:g}; use strong protection, seek shade, and reapply outdoors"
    if uv >= 6:
        return f"UV {uv:g}; use sunscreen and seek shade"
    if uv >= 3:
        return f"UV {uv:g}; use normal daily sun protection"
    return f"UV {uv:g}; no extra sun protection is needed"


def _clothing_en(max_feels, points, rain_risk, strong_wind) -> str:
    if max_feels >= 32:
        text = "Wear a breathable light top and lightweight bottoms"
    elif max_feels >= 27:
        text = "Wear short sleeves or a thin shirt with lightweight bottoms"
    elif max_feels >= 22:
        text = "Short sleeves or a thin shirt should be comfortable"
    else:
        text = "Bring a light outer layer"
    if any((point.humidity_percent or 0) >= 80 for point in points):
        text += "; prefer breathable, quick-drying fabrics"
    if rain_risk >= 45:
        text += "; avoid shoes that absorb water easily"
    if strong_wind:
        text += "; bring a wind-resistant layer and secure loose items"
    return text


def _closing_en(thunder, heavy_rain, strong_wind, rain, max_feels, uv) -> str:
    if thunder:
        return "Limit outdoor exposure during thunderstorms and travel carefully."
    if heavy_rain:
        return "Watch for standing water and difficult travel conditions."
    if strong_wind:
        return "Watch for falling objects and secure your belongings."
    if max_feels >= DANGEROUS_HEAT_C:
        return "Avoid prolonged outdoor activity and keep hydrated."
    if rain >= 45:
        return "Rain is possible today; take care on the way home."
    if max_feels >= 32:
        return "It will be hot today; remember to drink water."
    if uv >= 6:
        return "Midday sunlight will be strong; remember sun protection."
    return "The weather should be comfortable. Have a good day."
