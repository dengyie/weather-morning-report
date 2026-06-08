"""Responsive, email-friendly HTML report rendering."""

from __future__ import annotations

from html import escape

from weather_morning_report.models import WeatherSnapshot
from weather_morning_report.recommendations import ReportAdvice


def render_html(
    snapshot: WeatherSnapshot,
    advice: ReportAdvice,
    *,
    cached: bool = False,
    recipient_name: str = "",
    language: str = "zh-CN",
    report_type: str = "morning",
    greeting_visible: bool = True,
    footer_text: str = "",
    accent_color: str = "#2878b5",
    data_source_visible: bool = True,
) -> str:
    if language == "en":
        return _render_english(
            snapshot, advice, cached, recipient_name, report_type,
            greeting_visible, footer_text, accent_color, data_source_visible,
        )
    period_rows = "".join(
        f"""
        <tr>
          <th>{escape(period.label)}</th>
          <td>{escape(period.summary)}</td>
        </tr>"""
        for period in advice.periods
    )
    cache_notice = (
        f"""
        <div class="notice">
          实时天气源暂时不可用，以下建议基于
          {snapshot.fetched_at:%Y-%m-%d %H:%M %Z} 的缓存数据。
        </div>"""
        if cached
        else ""
    )
    greeting_word = {"morning": "早上好。", "midday": "中午好。", "evening": "晚上好。"}[report_type]
    greeting = f"{escape(recipient_name.strip())}，{greeting_word}" if recipient_name.strip() else greeting_word
    greeting_html = f"<p>{greeting}</p>" if greeting_visible else ""
    footer_html = f'<p class="closing">{escape(footer_text.strip())}</p>' if footer_text.strip() else ""
    source_html = (
        f'<p class="muted">数据来源：{escape(snapshot.source)}；获取时间：{snapshot.fetched_at:%Y-%m-%d %H:%M %Z}</p>'
        if data_source_visible else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(advice.subject)}</title>
  <style>
    body {{ margin: 0; background: #f3f6f8; color: #24313a; font-family: Arial, sans-serif; }}
    .wrap {{ max-width: 640px; margin: 0 auto; padding: 20px 12px; }}
    .card {{ background: #ffffff; border-radius: 14px; padding: 22px; }}
    h1 {{ margin: 0 0 8px; color: #17324d; font-size: 24px; line-height: 1.35; }}
    h2 {{ margin: 24px 0 10px; color: #17324d; font-size: 17px; }}
    p {{ margin: 8px 0; line-height: 1.65; }}
    .muted {{ color: #667884; font-size: 13px; }}
    .focus {{ margin: 18px 0; border-left: 4px solid {escape(accent_color)}; background: #edf6fc; padding: 12px 14px; }}
    .summary {{ width: 100%; border-spacing: 0 8px; }}
    .summary th {{ width: 64px; color: #557180; text-align: left; vertical-align: top; }}
    .summary td {{ font-weight: bold; }}
    .clothing {{ background: #f6f8f9; border-radius: 10px; padding: 12px 14px; }}
    .periods {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    .periods th, .periods td {{ border-bottom: 1px solid #e4eaee; padding: 11px 4px; text-align: left; }}
    .periods th {{ width: 70px; color: #557180; }}
    .notice {{ margin-bottom: 16px; border-radius: 8px; background: #fff4d6; color: #715711; padding: 10px 12px; font-size: 13px; line-height: 1.5; }}
    .closing {{ margin-top: 22px; color: #405966; }}
    @media (max-width: 480px) {{
      .wrap {{ padding: 0; }}
      .card {{ border-radius: 0; padding: 18px; }}
      h1 {{ font-size: 21px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <main class="card">
      {cache_notice}
      <p class="muted">天气早报</p>
      <h1>{escape(advice.focus)}</h1>
      {greeting_html}

      <div class="focus">
        <table class="summary" role="presentation">
          <tr><th>带伞</th><td>{escape(advice.umbrella)}</td></tr>
          <tr><th>防晒</th><td>{escape(advice.sunscreen)}</td></tr>
        </table>
      </div>

      <h2>穿搭建议</h2>
      <p class="clothing">{escape(advice.clothing)}</p>

      <h2>关键时段</h2>
      <table class="periods">
        {period_rows}
      </table>

      <h2>天气详情</h2>
      <p>
        当前 {escape(snapshot.current.description)}，
        {snapshot.current.temperature_c:g}°C，体感 {snapshot.current.feels_like_c:g}°C。
        今日 {snapshot.daily.minimum_temperature_c:g}°C -
        {snapshot.daily.maximum_temperature_c:g}°C。
      </p>

      <p class="closing">{escape(advice.closing)}</p>
      {footer_html}
      {source_html}
    </main>
  </div>
</body>
</html>
"""


def _render_english(
    snapshot, advice, cached, recipient_name, report_type,
    greeting_visible, footer_text, accent_color, data_source_visible,
) -> str:
    rows = "".join(
        f"<tr><th>{escape(period.label)}</th><td>{escape(period.summary)}</td></tr>"
        for period in advice.periods
    )
    notice = (
        f'<div class="notice">Live providers are unavailable; using cached data from {snapshot.fetched_at:%Y-%m-%d %H:%M %Z}.</div>'
        if cached else ""
    )
    greeting_word = {"morning": "Good morning", "midday": "Good afternoon", "evening": "Good evening"}[report_type]
    greeting = f"{greeting_word}, {escape(recipient_name.strip())}." if recipient_name.strip() else f"{greeting_word}."
    greeting_html = f"<p>{greeting}</p>" if greeting_visible else ""
    footer_html = f"<p>{escape(footer_text.strip())}</p>" if footer_text.strip() else ""
    source_html = (
        f"<p>Source: {escape(snapshot.source)}; fetched: {snapshot.fetched_at:%Y-%m-%d %H:%M %Z}</p>"
        if data_source_visible else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(advice.subject)}</title>
<style>body{{margin:0;background:#f3f6f8;color:#24313a;font-family:Arial,sans-serif}}main{{max-width:640px;margin:auto;background:white;padding:24px;border-top:4px solid {escape(accent_color)}}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #e4eaee}}.notice{{padding:10px;background:#fff4d6}}</style>
</head><body><main>{notice}<h1>{escape(advice.focus)}</h1>{greeting_html}
<p><strong>Umbrella:</strong> {escape(advice.umbrella)}</p>
<p><strong>Sun protection:</strong> {escape(advice.sunscreen)}</p>
<p><strong>Clothing:</strong> {escape(advice.clothing)}</p>
<h2>Key periods</h2><table>{rows}</table>
<p>{escape(advice.closing)}</p>{footer_html}{source_html}
</main></body></html>
"""
