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
) -> str:
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
    greeting = (
        f"{escape(recipient_name.strip())}，早上好。"
        if recipient_name.strip()
        else "早上好。"
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
    .focus {{ margin: 18px 0; border-left: 4px solid #2878b5; background: #edf6fc; padding: 12px 14px; }}
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
      <p>{greeting}</p>

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
      <p class="muted">
        数据来源：{escape(snapshot.source)}；
        获取时间：{snapshot.fetched_at:%Y-%m-%d %H:%M %Z}
      </p>
    </main>
  </div>
</body>
</html>
"""
