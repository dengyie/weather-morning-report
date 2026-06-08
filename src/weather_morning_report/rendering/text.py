"""Plain-text report rendering."""

from weather_morning_report.models import WeatherSnapshot
from weather_morning_report.recommendations import ReportAdvice


def render_text(
    snapshot: WeatherSnapshot,
    advice: ReportAdvice,
    *,
    cached: bool = False,
    recipient_name: str = "",
    language: str = "zh-CN",
    report_type: str = "morning",
    greeting_visible: bool = True,
    footer_text: str = "",
    data_source_visible: bool = True,
) -> str:
    separator = ": " if language == "en" else "："
    period_lines = "\n".join(f"{period.label}{separator}{period.summary}" for period in advice.periods)
    if language == "en":
        return _render_english(
            snapshot, advice, cached, recipient_name, period_lines, report_type,
            greeting_visible, footer_text, data_source_visible,
        )
    cache_notice = (
        f"注意：实时天气源暂时不可用，以下建议基于 {snapshot.fetched_at:%Y-%m-%d %H:%M %Z} 的缓存数据。\n\n"
        if cached
        else ""
    )
    greeting_word = {"morning": "早上好。", "midday": "中午好。", "evening": "晚上好。"}[report_type]
    greeting = f"{recipient_name.strip()}，{greeting_word}" if recipient_name.strip() else greeting_word
    greeting = f"{greeting}\n\n" if greeting_visible else ""
    footer = f"\n{footer_text.strip()}\n" if footer_text.strip() else ""
    source = (
        f"\n数据来源：{snapshot.source}，获取时间：{snapshot.fetched_at:%Y-%m-%d %H:%M %Z}\n"
        if data_source_visible else ""
    )
    return f"""主题：{advice.subject}

{cache_notice}{greeting}今日重点：{advice.focus}

带伞：{advice.umbrella}
防晒：{advice.sunscreen}

穿搭：{advice.clothing}

当前：{snapshot.current.description}，{snapshot.current.temperature_c:g}°C，体感 {snapshot.current.feels_like_c:g}°C
今日温度：{snapshot.daily.minimum_temperature_c:g}°C - {snapshot.daily.maximum_temperature_c:g}°C

关键时段
{period_lines}

{advice.closing}
{footer}{source}
"""


def _render_english(
    snapshot, advice, cached, recipient_name, period_lines, report_type,
    greeting_visible, footer_text, data_source_visible,
) -> str:
    notice = (
        f"Note: live providers are unavailable; this report uses cached data from {snapshot.fetched_at:%Y-%m-%d %H:%M %Z}.\n\n"
        if cached else ""
    )
    greeting_word = {"morning": "Good morning", "midday": "Good afternoon", "evening": "Good evening"}[report_type]
    greeting = f"{greeting_word}, {recipient_name.strip()}." if recipient_name.strip() else f"{greeting_word}."
    greeting = f"{greeting}\n\n" if greeting_visible else ""
    footer = f"\n{footer_text.strip()}\n" if footer_text.strip() else ""
    source = (
        f"\nSource: {snapshot.source}; fetched: {snapshot.fetched_at:%Y-%m-%d %H:%M %Z}\n"
        if data_source_visible else ""
    )
    return f"""Subject: {advice.subject}

{notice}{greeting}Focus: {advice.focus}
Umbrella: {advice.umbrella}
Sun protection: {advice.sunscreen}

Clothing: {advice.clothing}

Current: {snapshot.current.description}, {snapshot.current.temperature_c:g}°C, feels like {snapshot.current.feels_like_c:g}°C
Today's range: {snapshot.daily.minimum_temperature_c:g}°C - {snapshot.daily.maximum_temperature_c:g}°C

Key periods
{period_lines}

{advice.closing}
{footer}{source}
"""
