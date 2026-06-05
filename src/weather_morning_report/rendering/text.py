"""Plain-text report rendering."""

from weather_morning_report.models import WeatherSnapshot
from weather_morning_report.recommendations import ReportAdvice


def render_text(
    snapshot: WeatherSnapshot,
    advice: ReportAdvice,
    *,
    cached: bool = False,
) -> str:
    period_lines = "\n".join(
        f"{period.label}：{period.summary}" for period in advice.periods
    )
    cache_notice = (
        f"注意：实时天气源暂时不可用，以下建议基于 {snapshot.fetched_at:%Y-%m-%d %H:%M %Z} 的缓存数据。\n\n"
        if cached
        else ""
    )
    return f"""主题：{advice.subject}

{cache_notice}早上好。

今日重点：{advice.focus}
带伞：{advice.umbrella}
防晒：{advice.sunscreen}

穿搭：{advice.clothing}

当前：{snapshot.current.description}，{snapshot.current.temperature_c:g}°C，体感 {snapshot.current.feels_like_c:g}°C
今日温度：{snapshot.daily.minimum_temperature_c:g}°C - {snapshot.daily.maximum_temperature_c:g}°C

关键时段
{period_lines}

{advice.closing}

数据来源：{snapshot.source}，获取时间：{snapshot.fetched_at:%Y-%m-%d %H:%M %Z}
"""
