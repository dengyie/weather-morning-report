"""Responsive, email-friendly HTML report rendering."""

from __future__ import annotations

from html import escape

from weather_morning_report.email_templates import (
    email_template_label,
    normalize_email_template,
)
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
    email_template: str = "1",
) -> str:
    context = _context(
        snapshot,
        advice,
        cached=cached,
        recipient_name=recipient_name,
        language=language,
        report_type=report_type,
        greeting_visible=greeting_visible,
        footer_text=footer_text,
        accent_color=accent_color,
        data_source_visible=data_source_visible,
        email_template=normalize_email_template(email_template),
    )
    return {
        "1": _render_warm,
        "2": _render_action,
        "3": _render_glass_gradient,
        "4": _render_minimal,
        "5": _render_dashboard,
    }[context["email_template"]](context)


def _context(
    snapshot: WeatherSnapshot,
    advice: ReportAdvice,
    *,
    cached: bool,
    recipient_name: str,
    language: str,
    report_type: str,
    greeting_visible: bool,
    footer_text: str,
    accent_color: str,
    data_source_visible: bool,
    email_template: str,
) -> dict[str, str]:
    english = language == "en"
    labels = _english_labels() if english else _chinese_labels()
    greeting_word = labels["greetings"][report_type]
    name = recipient_name.strip()
    if english:
        greeting = f"{greeting_word}, {escape(name)}." if name else f"{greeting_word}."
    else:
        greeting = f"{escape(name)}，{greeting_word}" if name else greeting_word
    period_rows = "".join(
        f"<tr><th>{escape(period.label)}</th><td>{escape(period.summary)}</td></tr>"
        for period in advice.periods
    )
    compact_periods = "".join(
        f"""
        <tr>
          <td><strong>{escape(period.label)}</strong></td>
          <td>{escape(period.summary)}</td>
        </tr>"""
        for period in advice.periods
    )
    cache_notice = (
        f'<div class="notice">{labels["cache_notice"]} {snapshot.fetched_at:%Y-%m-%d %H:%M %Z}.</div>'
        if cached
        else ""
    )
    footer_html = (
        f'<p class="closing">{escape(footer_text.strip())}</p>'
        if footer_text.strip()
        else ""
    )
    source_html = (
        f'<p class="muted">{labels["source"]}{escape(snapshot.source)}; {labels["fetched"]}{snapshot.fetched_at:%Y-%m-%d %H:%M %Z}</p>'
        if data_source_visible
        else ""
    )
    template_label = email_template_label(email_template)
    return {
        "html_lang": "en" if english else "zh-CN",
        "title": escape(advice.subject),
        "report_label": labels["report"],
        "location": escape(snapshot.location.name),
        "template_label": template_label,
        "email_template": email_template,
        "accent": escape(accent_color),
        "focus": escape(advice.focus),
        "greeting_html": f"<p>{greeting}</p>" if greeting_visible else "",
        "cache_notice": cache_notice,
        "umbrella_label": labels["umbrella"],
        "sunscreen_label": labels["sunscreen"],
        "clothing_label": labels["clothing"],
        "periods_label": labels["periods"],
        "details_label": labels["details"],
        "risk_label": labels["risk"],
        "checklist_label": labels["checklist"],
        "commute_label": labels["commute"],
        "rain_label": labels["rain"],
        "range_label": labels["range"],
        "feels_label": labels["feels"],
        "wind_label": labels["wind"],
        "wind_unit": labels["wind_unit"],
        "umbrella": escape(advice.umbrella),
        "sunscreen": escape(advice.sunscreen),
        "clothing": escape(advice.clothing),
        "closing": escape(advice.closing),
        "current_description": escape(snapshot.current.description),
        "current_temp": f"{snapshot.current.temperature_c:g}",
        "feels_like": f"{snapshot.current.feels_like_c:g}",
        "min_temp": f"{snapshot.daily.minimum_temperature_c:g}",
        "max_temp": f"{snapshot.daily.maximum_temperature_c:g}",
        "uv": f"{snapshot.daily.uv_index:g}" if snapshot.daily.uv_index is not None else "-",
        "wind": (
            f"{snapshot.current.wind_speed_kph:g}"
            if snapshot.current.wind_speed_kph is not None
            else "-"
        ),
        "risk_level": str(advice.signals.highest_risk_level),
        "period_rows": period_rows,
        "compact_periods": compact_periods,
        "footer_html": footer_html,
        "source_html": source_html,
    }


def _weather_visual(c: dict[str, str], tone: str) -> str:
    return f"""
        <div class="weather-visual weather-visual-{tone}" aria-hidden="true">
          <svg viewBox="0 0 180 150" role="img">
            <defs>
              <linearGradient id="sky-{tone}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="currentColor" stop-opacity=".34"/>
                <stop offset="100%" stop-color="currentColor" stop-opacity=".08"/>
              </linearGradient>
              <filter id="soft-{tone}" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="7"/>
              </filter>
            </defs>
            <circle cx="58" cy="52" r="30" fill="currentColor" opacity=".24" filter="url(#soft-{tone})"/>
            <circle cx="58" cy="52" r="22" fill="currentColor" opacity=".9"/>
            <path d="M58 14v13M58 77v13M20 52h13M83 52h13M31 25l9 9M76 70l9 9M85 25l-9 9M40 70l-9 9" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity=".55"/>
            <path d="M60 98c7-17 22-28 41-28 22 0 39 15 43 36 14 3 24 14 24 28 0 17-14 30-32 30H57c-18 0-32-13-32-30 0-15 11-27 26-29 2-2 5-5 9-7z" fill="url(#sky-{tone})" stroke="currentColor" stroke-width="3" opacity=".95"/>
            <path d="M75 126c8 10 20 10 28 0 8 10 20 10 28 0" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity=".5"/>
          </svg>
          <div class="visual-temp">{c["current_temp"]}°</div>
        </div>
"""


def _action_cards(c: dict[str, str]) -> str:
    return f"""
        <div class="action-cards">
          <section class="action-card action-umbrella">
            <span class="action-kicker">{c["umbrella_label"]}</span>
            <strong>{c["umbrella"]}</strong>
          </section>
          <section class="action-card action-sunscreen">
            <span class="action-kicker">{c["sunscreen_label"]}</span>
            <strong>{c["sunscreen"]}</strong>
          </section>
          <section class="action-card action-clothing">
            <span class="action-kicker">{c["clothing_label"]}</span>
            <strong>{c["clothing"]}</strong>
          </section>
        </div>
"""


def _metric_strip(c: dict[str, str]) -> str:
    return f"""
        <div class="metric-strip">
          <div><span>{c["details_label"]}</span><strong>{c["current_temp"]}°C</strong><em>{c["current_description"]}</em></div>
          <div><span>{c["range_label"]}</span><strong>{c["min_temp"]}°-{c["max_temp"]}°</strong><em>{c["feels_label"]} {c["feels_like"]}°C</em></div>
          <div><span>UV</span><strong>{c["uv"]}</strong><em>{c["sunscreen_label"]}</em></div>
          <div><span>{c["wind_label"]}</span><strong>{c["wind"]}</strong><em>{c["wind_unit"]}</em></div>
        </div>
"""


def _period_cards(c: dict[str, str]) -> str:
    return f"""
        <section class="period-card">
          <h2>{c["periods_label"]}</h2>
          <table class="periods">{c["period_rows"]}</table>
        </section>
"""


def _render_warm(c: dict[str, str]) -> str:
    return _page(
        c,
        """
    body { margin: 0; background: radial-gradient(circle at 12% 0%, #fff8ec 0, transparent 34%), radial-gradient(circle at 88% 6%, #f3d1a6 0, transparent 36%), linear-gradient(145deg, #f7efe4 0%, #ecd9c0 100%); color: #2f2b25; font-family: Arial, sans-serif; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 34px 16px; }
    .card { background: linear-gradient(180deg, rgba(255,250,243,.96) 0%, rgba(255,246,234,.96) 100%); border-radius: 32px; padding: 34px; border: 1px solid rgba(255,255,255,.75); box-shadow: 0 28px 90px rgba(112,76,38,.24), inset 0 1px 0 rgba(255,255,255,.9); }
    .masthead { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
    .eyebrow { color: #8a6243; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; }
    .template-pill { border: 1px solid rgba(138,98,67,.22); color: #8a6243; background: rgba(255,255,255,.48); padding: 7px 11px; border-radius: 999px; font-size: 12px; }
    .hero { display: grid; grid-template-columns: minmax(0,1fr) 170px; gap: 22px; align-items: center; margin: 20px 0 22px; border-left: 6px solid var(--accent); background: linear-gradient(135deg, rgba(255,242,218,.92) 0%, rgba(255,233,200,.88) 100%); padding: 22px; border-radius: 26px; box-shadow: inset 0 1px 0 rgba(255,255,255,.78), 0 18px 46px rgba(159,105,45,.14); }
    h1 { margin: 10px 0 12px; color: #3b2f25; font-size: 34px; line-height: 1.2; letter-spacing: -.02em; }
    h2 { margin: 24px 0 12px; color: #4b3828; font-size: 18px; }
    p { margin: 8px 0; line-height: 1.68; }
    .muted { color: #77685a; font-size: 13px; }
    .weather-visual { color: #d98535; position: relative; min-height: 140px; display: grid; place-items: center; }
    .weather-visual svg { width: 170px; height: 140px; }
    .visual-temp { position: absolute; right: 4px; bottom: 8px; padding: 7px 13px; background: rgba(255,255,255,.78); border-radius: 999px; box-shadow: 0 10px 26px rgba(120,74,29,.18); font-weight: 800; }
    .action-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .action-card { background: rgba(255,255,255,.72); border: 1px solid rgba(232,203,166,.7); border-radius: 20px; padding: 15px; box-shadow: 0 12px 30px rgba(117,78,36,.1); }
    .action-clothing { grid-column: 1 / -1; }
    .action-kicker { display: block; color: #8a6243; font-size: 12px; font-weight: 700; margin-bottom: 7px; }
    .action-card strong { display: block; line-height: 1.55; color: #362b20; }
    .period-card { margin-top: 22px; background: rgba(255,255,255,.5); border-radius: 22px; padding: 18px; }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods th, .periods td { border-bottom: 1px solid #ead8c1; padding: 12px 4px; text-align: left; }
    .periods th { width: 74px; color: #7b5a3f; }
    .notice { margin-bottom: 16px; border-radius: 14px; background: #fff0c4; color: #654f10; padding: 11px 13px; font-size: 13px; line-height: 1.5; }
    .closing { margin-top: 22px; color: #5e4a39; }
""",
        f"""
      {c["cache_notice"]}
      <header class="masthead"><p class="eyebrow">{c["report_label"]} · {c["location"]}</p><span class="template-pill">{c["template_label"]}</span></header>
      <div class="hero">
        <div>
          <h1>{c["focus"]}</h1>
          {c["greeting_html"]}
          <p>{c["current_description"]} · {c["min_temp"]}°C - {c["max_temp"]}°C · {c["feels_label"]} {c["feels_like"]}°C</p>
        </div>
        {_weather_visual(c, "warm")}
      </div>
      {_action_cards(c)}
      {_period_cards(c)}
      <p class="closing">{c["closing"]}</p>
      {c["footer_html"]}
      {c["source_html"]}
""",
    )


def _render_action(c: dict[str, str]) -> str:
    return _page(
        c,
        """
    body { margin: 0; background: radial-gradient(circle at 94% 0%, #bde7ff 0, transparent 32%), linear-gradient(160deg, #eaf5ff 0%, #f7fbff 46%, #e6eef6 100%); color: #132432; font-family: Arial, sans-serif; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 34px 16px; }
    .card { background: rgba(255,255,255,.97); border-radius: 30px; padding: 28px; border: 1px solid rgba(215,230,240,.95); box-shadow: 0 30px 86px rgba(32,78,110,.18); }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-bottom: 18px; }
    .eyebrow, .muted { color: #567083; font-size: 13px; }
    .eyebrow { margin: 0; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
    .template-pill { color: #0d4f78; background: #e6f5ff; border: 1px solid #c7e7fb; border-radius: 999px; padding: 7px 11px; font-size: 12px; font-weight: 700; }
    .hero { display: grid; grid-template-columns: minmax(0,1.1fr) minmax(210px,.9fr); gap: 14px; margin-bottom: 14px; }
    .command { background: linear-gradient(135deg, #0f4265 0%, #126d8d 100%); color: #f5fbff; border-radius: 26px; padding: 24px; min-height: 250px; position: relative; overflow: hidden; box-shadow: 0 22px 54px rgba(15,66,101,.24); }
    .command:after { content: ""; position: absolute; right: -56px; top: -54px; width: 180px; height: 180px; border-radius: 999px; background: rgba(255,255,255,.13); }
    .command h1 { position: relative; margin: 12px 0; font-size: 31px; line-height: 1.18; letter-spacing: -.03em; }
    .command p { position: relative; color: rgba(245,251,255,.9); }
    .live-temp { position: relative; display: inline-flex; align-items: flex-end; gap: 8px; margin-top: 16px; font-weight: 800; font-size: 54px; line-height: 1; }
    .live-temp span { padding-bottom: 7px; font-size: 14px; font-weight: 700; color: rgba(245,251,255,.78); }
    .priority { display: grid; gap: 12px; }
    .priority-card { border-radius: 22px; padding: 16px; background: linear-gradient(180deg, #f8fcff 0%, #eef7fc 100%); border: 1px solid #dcecf5; box-shadow: inset 0 1px 0 rgba(255,255,255,.86); }
    .priority-card b { display: block; color: #567083; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 7px; }
    .priority-card strong { color: #132432; font-size: 15px; line-height: 1.5; }
    .action-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 14px 0; }
    .action-card { min-height: 118px; background: #ffffff; border: 1px solid #daeaf4; border-radius: 22px; padding: 16px; box-shadow: 0 14px 32px rgba(38,83,112,.1); }
    .action-card:before { content: ""; display: block; width: 34px; height: 4px; border-radius: 99px; background: var(--accent); margin-bottom: 14px; }
    .action-kicker { display: block; color: #567083; font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 7px; }
    .action-card strong { display: block; color: #142a3a; line-height: 1.55; }
    .metric-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 12px 0 18px; }
    .metric-strip div { background: #eef6fb; border-radius: 18px; padding: 13px; border: 1px solid #d7e8f2; }
    .metric-strip span, .metric-strip em { display: block; color: #60798c; font-size: 12px; font-style: normal; }
    .metric-strip strong { display: block; color: #102c44; font-size: 22px; margin: 4px 0; }
    .period-card { background: #f8fbfd; border: 1px solid #dce8ef; border-radius: 24px; padding: 18px; }
    h2 { margin: 0 0 10px; color: #102c44; font-size: 16px; }
    p { margin: 8px 0; line-height: 1.62; }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods th, .periods td { border-bottom: 1px solid #dce8ef; padding: 11px 4px; text-align: left; }
    .periods th { width: 74px; color: #526c7d; }
    .notice { margin-bottom: 16px; border-radius: 14px; background: #fff4d6; color: #715711; padding: 11px 13px; font-size: 13px; line-height: 1.5; }
    .closing { margin-top: 18px; color: #405966; }
""",
        f"""
      {c["cache_notice"]}
      <header class="topbar"><p class="eyebrow">{c["report_label"]} · {c["location"]}</p><span class="template-pill">{c["template_label"]}</span></header>
      <section class="hero">
        <div class="command">
          <p>{c["details_label"]}</p>
          <h1>{c["focus"]}</h1>
          {c["greeting_html"]}
          <div class="live-temp">{c["current_temp"]}°<span>{c["current_description"]}</span></div>
        </div>
        <div class="priority">
          <section class="priority-card"><b>{c["range_label"]}</b><strong>{c["min_temp"]}°C - {c["max_temp"]}°C · {c["feels_label"]} {c["feels_like"]}°C</strong></section>
          <section class="priority-card"><b>{c["risk_label"]}</b><strong>{c["risk_level"]}</strong></section>
        </div>
      </section>
      {_action_cards(c)}
      {_metric_strip(c)}
      {_period_cards(c)}
      <p class="closing">{c["closing"]}</p>
      {c["footer_html"]}
      {c["source_html"]}
""",
    )


def _render_glass_gradient(c: dict[str, str]) -> str:
    return _page(
        c,
        """
    body { margin: 0; background: radial-gradient(circle at 12% 7%, rgba(85,205,255,.55) 0, transparent 30%), radial-gradient(circle at 92% 16%, rgba(190,139,255,.5) 0, transparent 34%), radial-gradient(circle at 62% 92%, rgba(109,255,196,.42) 0, transparent 36%), linear-gradient(140deg, #dff7ff 0%, #f2ecff 48%, #e9fff5 100%); color: #10243a; font-family: Arial, sans-serif; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 34px 16px; }
    .card { position: relative; overflow: hidden; background: linear-gradient(135deg, rgba(255,255,255,.62) 0%, rgba(242,248,255,.5) 42%, rgba(244,255,251,.62) 100%); border-radius: 34px; padding: 30px; border: 1px solid rgba(255,255,255,.82); box-shadow: 0 34px 96px rgba(64,84,124,.24); backdrop-filter: blur(22px); }
    .card:before { content: ""; position: absolute; inset: 12px; border-radius: 28px; border: 1px solid rgba(255,255,255,.58); pointer-events: none; }
    .glass-top { position: relative; display: flex; justify-content: space-between; gap: 14px; align-items: center; margin-bottom: 18px; }
    .eyebrow, .muted { color: #49657a; font-size: 13px; }
    .eyebrow { margin: 0; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .template-pill { color: #244e69; background: rgba(255,255,255,.46); border: 1px solid rgba(255,255,255,.74); border-radius: 999px; padding: 7px 11px; font-size: 12px; backdrop-filter: blur(10px); }
    .hero-glass { position: relative; display: grid; grid-template-columns: minmax(0,1fr) 190px; align-items: center; gap: 18px; padding: 24px; border-radius: 28px; background: rgba(255,255,255,.42); border: 1px solid rgba(255,255,255,.78); box-shadow: inset 0 1px 0 rgba(255,255,255,.84), 0 18px 48px rgba(77,95,133,.13); backdrop-filter: blur(14px); }
    h1 { margin: 10px 0 12px; color: #10243a; font-size: 33px; line-height: 1.18; letter-spacing: -.03em; }
    h2 { margin: 0 0 10px; color: #17324d; font-size: 16px; }
    p { margin: 8px 0; line-height: 1.64; }
    .weather-visual { color: #278fc6; position: relative; min-height: 150px; display: grid; place-items: center; }
    .weather-visual svg { width: 182px; height: 152px; filter: drop-shadow(0 18px 26px rgba(39,143,198,.18)); }
    .visual-temp { position: absolute; right: 0; bottom: 5px; padding: 8px 14px; background: rgba(255,255,255,.62); border: 1px solid rgba(255,255,255,.82); border-radius: 999px; box-shadow: 0 14px 32px rgba(77,95,133,.14); font-weight: 800; backdrop-filter: blur(10px); }
    .glass-grid { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 14px 0; }
    .glass-panel { background: rgba(255,255,255,.48); border: 1px solid rgba(255,255,255,.76); border-radius: 22px; padding: 16px; box-shadow: 0 12px 32px rgba(77,95,133,.12); backdrop-filter: blur(12px); }
    .glass-panel.wide { grid-column: 1 / -1; }
    .glass-panel b { display: block; color: #36546b; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 7px; }
    .metric-strip { position: relative; display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 14px 0; }
    .metric-strip div { background: rgba(255,255,255,.42); border: 1px solid rgba(255,255,255,.72); border-radius: 18px; padding: 13px; backdrop-filter: blur(10px); }
    .metric-strip span, .metric-strip em { display: block; color: #557087; font-size: 12px; font-style: normal; }
    .metric-strip strong { display: block; color: #10243a; font-size: 22px; margin: 4px 0; }
    .period-card { position: relative; background: rgba(255,255,255,.48); border: 1px solid rgba(255,255,255,.76); border-radius: 24px; padding: 18px; backdrop-filter: blur(12px); }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods th, .periods td { border-bottom: 1px solid rgba(75,107,130,.18); padding: 11px 4px; text-align: left; }
    .periods th { width: 74px; color: #52677c; }
    .notice { position: relative; margin-bottom: 16px; border-radius: 14px; background: rgba(255,244,214,.75); color: #715711; padding: 11px 13px; font-size: 13px; line-height: 1.5; }
    .closing { position: relative; margin-top: 18px; color: #2f4a5f; }
""",
        f"""
      {c["cache_notice"]}
      <header class="glass-top"><p class="eyebrow">{c["report_label"]} · {c["location"]}</p><span class="template-pill">{c["template_label"]}</span></header>
      <section class="hero-glass">
        <div>
          <h1>{c["focus"]}</h1>
          {c["greeting_html"]}
          <p>{c["current_description"]} · {c["min_temp"]}°C - {c["max_temp"]}°C · {c["feels_label"]} {c["feels_like"]}°C</p>
        </div>
        {_weather_visual(c, "glass")}
      </section>
      <div class="glass-grid">
        <section class="glass-panel"><b>{c["umbrella_label"]}</b>{c["umbrella"]}</section>
        <section class="glass-panel"><b>{c["sunscreen_label"]}</b>{c["sunscreen"]}</section>
        <section class="glass-panel wide"><b>{c["clothing_label"]}</b>{c["clothing"]}</section>
      </div>
      {_metric_strip(c)}
      {_period_cards(c)}
      <p class="closing">{c["closing"]}</p>
      {c["footer_html"]}
      {c["source_html"]}
""",
    )


def _render_minimal(c: dict[str, str]) -> str:
    return _page(
        c,
        """
    body { margin: 0; background: #f7f7f2; color: #151a1e; font-family: Arial, sans-serif; }
    .wrap { max-width: 690px; margin: 0 auto; padding: 34px 16px; }
    .card { background: #fffffb; border-radius: 0; padding: 42px; border: 1px solid #e4e3dc; box-shadow: 0 18px 56px rgba(31,41,48,.08); }
    .minimal-head { display: grid; grid-template-columns: 1fr auto; gap: 20px; align-items: start; border-bottom: 1px solid #deded6; padding-bottom: 24px; }
    .eyebrow, .muted { color: #6c7478; font-size: 13px; }
    .eyebrow { margin: 0 0 14px; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; }
    .template-pill { color: #444b4f; border: 1px solid #deded6; border-radius: 999px; padding: 7px 11px; font-size: 12px; }
    .temperature-lockup { color: #11181d; text-align: right; font-size: 58px; font-weight: 800; letter-spacing: -.06em; line-height: .95; }
    .temperature-lockup span { display: block; color: #7a8286; font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-top: 8px; }
    h1 { margin: 0 0 14px; color: #11181d; font-size: 34px; line-height: 1.18; letter-spacing: -.03em; font-weight: 800; }
    h2 { margin: 28px 0 10px; color: #11181d; font-size: 12px; letter-spacing: .16em; text-transform: uppercase; }
    p { margin: 8px 0; line-height: 1.74; }
    .summary-line { color: #4a5358; font-size: 15px; }
    .minimal-actions { display: grid; grid-template-columns: 1fr; border-top: 1px solid #deded6; margin-top: 24px; }
    .minimal-row { display: grid; grid-template-columns: 112px 1fr; gap: 18px; border-bottom: 1px solid #deded6; padding: 16px 0; }
    .minimal-row b { color: #6c7478; font-size: 13px; font-weight: 500; }
    .minimal-row span { color: #151a1e; line-height: 1.65; }
    .period-card { margin-top: 26px; border-top: 2px solid #151a1e; padding-top: 4px; }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods th, .periods td { border-bottom: 1px solid #e6e6df; padding: 13px 0; text-align: left; }
    .periods th { width: 76px; color: #6c7478; font-weight: 500; }
    .notice { margin-bottom: 18px; border-left: 3px solid #c39b3b; background: #fff9e8; color: #5d4b18; padding: 10px 12px; font-size: 13px; line-height: 1.5; }
    .closing { margin-top: 22px; color: #3f4b52; }
""",
        f"""
      {c["cache_notice"]}
      <header class="minimal-head">
        <div>
          <p class="eyebrow">{c["report_label"]} · {c["location"]}</p>
          <h1>{c["focus"]}</h1>
          {c["greeting_html"]}
          <p class="summary-line">{c["current_description"]} / {c["min_temp"]}°C - {c["max_temp"]}°C / {c["feels_label"]} {c["feels_like"]}°C</p>
        </div>
        <div>
          <span class="template-pill">{c["template_label"]}</span>
          <div class="temperature-lockup">{c["current_temp"]}°<span>{c["details_label"]}</span></div>
        </div>
      </header>
      <section class="minimal-actions">
        <div class="minimal-row"><b>{c["umbrella_label"]}</b><span>{c["umbrella"]}</span></div>
        <div class="minimal-row"><b>{c["sunscreen_label"]}</b><span>{c["sunscreen"]}</span></div>
        <div class="minimal-row"><b>{c["clothing_label"]}</b><span>{c["clothing"]}</span></div>
      </section>
      {_period_cards(c)}
      <p class="closing">{c["closing"]}</p>
      {c["footer_html"]}
      {c["source_html"]}
""",
    )


def _render_dashboard(c: dict[str, str]) -> str:
    return _page(
        c,
        """
    body { margin: 0; background: radial-gradient(circle at 0% 0%, #dbeafe 0, transparent 36%), linear-gradient(145deg, #e8eef4 0%, #d9e2ea 100%); color: #17212b; font-family: Arial, sans-serif; }
    .wrap { max-width: 730px; margin: 0 auto; padding: 34px 16px; }
    .card { background: #f8fafc; border-radius: 30px; padding: 28px; border: 1px solid rgba(202,214,225,.96); box-shadow: 0 30px 86px rgba(37,54,73,.18); }
    .dash-head { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-bottom: 16px; }
    .eyebrow, .muted { color: #607080; font-size: 13px; }
    .eyebrow { margin: 0; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .template-pill { color: #273746; background: #edf3f8; border: 1px solid #d5e0e8; border-radius: 999px; padding: 7px 11px; font-size: 12px; }
    .status { display: grid; grid-template-columns: minmax(0,1fr) 160px; gap: 16px; align-items: center; background: linear-gradient(135deg, #102030 0%, #173d56 100%); color: #f5fbff; border-radius: 26px; padding: 22px; box-shadow: 0 22px 54px rgba(16,32,48,.22); }
    .risk-chip { display: inline-block; background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); color: #e9f7ff; border-radius: 999px; padding: 7px 11px; font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    h1 { margin: 12px 0 10px; color: #ffffff; font-size: 30px; line-height: 1.2; letter-spacing: -.03em; }
    h2 { margin: 22px 0 10px; color: #102030; font-size: 15px; letter-spacing: .1em; text-transform: uppercase; }
    p { margin: 8px 0; line-height: 1.62; }
    .weather-visual { color: #7ed2ff; position: relative; min-height: 134px; display: grid; place-items: center; }
    .weather-visual svg { width: 160px; height: 132px; }
    .visual-temp { position: absolute; right: 0; bottom: 0; padding: 7px 12px; color: #102030; background: #dff4ff; border-radius: 999px; font-weight: 800; }
    .metrics-board { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 14px 0; }
    .metric-box { background: #ffffff; border: 1px solid #dce4eb; border-radius: 20px; padding: 14px; box-shadow: inset 0 1px 0 rgba(255,255,255,.84); }
    .metric-box b { display: block; color: #607080; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 5px; }
    .metric-box span { display: block; color: #12283a; font-size: 25px; font-weight: 800; margin-bottom: 3px; }
    .ops-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: start; }
    .ops-panel { background: #ffffff; border: 1px solid #dce4eb; border-radius: 22px; padding: 18px; box-shadow: 0 14px 34px rgba(37,54,73,.08); }
    .checklist { width: 100%; border-collapse: collapse; }
    .checklist th, .checklist td { border-bottom: 1px solid #dce4eb; padding: 12px 0; text-align: left; vertical-align: top; }
    .checklist th { width: 90px; color: #526879; }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods td { border-bottom: 1px solid #dce4eb; padding: 12px 0; text-align: left; vertical-align: top; }
    .periods strong { color: #526879; }
    .notice { margin-bottom: 16px; border-radius: 14px; background: #fff4d6; color: #715711; padding: 11px 13px; font-size: 13px; line-height: 1.5; }
    .closing { margin-top: 18px; color: #40515e; }
""",
        f"""
      {c["cache_notice"]}
      <header class="dash-head"><p class="eyebrow">{c["report_label"]} · {c["location"]}</p><span class="template-pill">{c["template_label"]}</span></header>
      <section class="status">
        <div>
          <span class="risk-chip">{c["risk_label"]}: {c["risk_level"]}</span>
          <h1>{c["focus"]}</h1>
          {c["greeting_html"]}
        </div>
        {_weather_visual(c, "dashboard")}
      </section>
      <section class="metrics-board">
        <div class="metric-box"><b>{c["details_label"]}</b><span>{c["current_temp"]}°C</span>{c["current_description"]}</div>
        <div class="metric-box"><b>{c["range_label"]}</b><span>{c["min_temp"]}°-{c["max_temp"]}°</span>{c["feels_label"]} {c["feels_like"]}°C</div>
        <div class="metric-box"><b>UV</b><span>{c["uv"]}</span>{c["sunscreen_label"]}</div>
        <div class="metric-box"><b>{c["wind_label"]}</b><span>{c["wind"]}</span>{c["wind_unit"]}</div>
      </section>
      <section class="ops-grid">
        <div class="ops-panel">
          <h2>{c["checklist_label"]}</h2>
          <table class="checklist">
            <tr><th>{c["umbrella_label"]}</th><td>{c["umbrella"]}</td></tr>
            <tr><th>{c["clothing_label"]}</th><td>{c["clothing"]}</td></tr>
            <tr><th>{c["sunscreen_label"]}</th><td>{c["sunscreen"]}</td></tr>
          </table>
        </div>
        <div class="ops-panel">
          <h2>{c["periods_label"]}</h2>
          <table class="periods">{c["compact_periods"]}</table>
        </div>
      </section>
      <p class="closing">{c["closing"]}</p>
      {c["footer_html"]}
      {c["source_html"]}
""",
    )


def _page(c: dict[str, str], style: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="{c["html_lang"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c["title"]}</title>
  <style>
    :root {{ --accent: {c["accent"]}; color-scheme: light; }}
    * {{ box-sizing: border-box; }}
    body {{ -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }}
    table {{ max-width: 100%; }}
{style}
    @media (max-width: 480px) {{
      .wrap {{ padding: 0; }}
      .card {{ border-radius: 0; padding: 18px; }}
      h1 {{ font-size: 21px; }}
      .hero, .hero-glass, .minimal-head, .status, .ops-grid {{ display: block; }}
      .weather-visual {{ margin-top: 14px; }}
      .action-cards, .glass-grid, .metric-strip, .metrics-board {{ grid-template-columns: 1fr; }}
      .action-clothing, .glass-panel.wide {{ grid-column: auto; }}
      .minimal-head > div + div {{ margin-top: 18px; }}
      .temperature-lockup {{ text-align: left; font-size: 44px; }}
      .grid, .metrics, .actions {{ border-spacing: 0 8px; margin-left: 0; margin-right: 0; }}
      .grid td, .metrics td, .actions td {{ display: block; width: auto; margin-bottom: 8px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <main class="card" data-email-template="{c["email_template"]}" aria-label="{escape(c["template_label"])}">
{body}
    </main>
  </div>
</body>
</html>
"""


def _chinese_labels() -> dict[str, object]:
    return {
        "report": "天气早报",
        "umbrella": "带伞",
        "sunscreen": "防晒",
        "clothing": "穿搭建议",
        "periods": "关键时段",
        "details": "天气详情",
        "risk": "风险等级",
        "checklist": "行动清单",
        "commute": "通勤提醒",
        "rain": "降雨概率",
        "range": "温差",
        "feels": "体感",
        "wind": "风速",
        "wind_unit": "公里/小时",
        "source": "数据来源：",
        "fetched": "获取时间：",
        "cache_notice": "实时天气源暂时不可用，以下建议基于缓存数据：",
        "greetings": {"morning": "早上好。", "midday": "中午好。", "evening": "晚上好。"},
    }


def _english_labels() -> dict[str, object]:
    return {
        "report": "Weather Brief",
        "umbrella": "Umbrella",
        "sunscreen": "Sun protection",
        "clothing": "Clothing",
        "periods": "Key periods",
        "details": "Weather details",
        "risk": "Risk level",
        "checklist": "Action checklist",
        "commute": "Commute note",
        "rain": "Rain probability",
        "range": "Range",
        "feels": "Feels like",
        "wind": "Wind",
        "wind_unit": "kph",
        "source": "Source: ",
        "fetched": "fetched: ",
        "cache_notice": "Live providers are unavailable; using cached data from",
        "greetings": {
            "morning": "Good morning",
            "midday": "Good afternoon",
            "evening": "Good evening",
        },
    }
