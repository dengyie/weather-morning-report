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
        "current_condition": snapshot.current.condition.value,
        "current_condition_class": snapshot.current.condition.value.replace("_", "-"),
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
    condition = c["current_condition"]
    condition_class = condition.replace("_", "-")
    palette = _weather_palette(tone)
    scene = _weather_scene(condition, condition_class)
    return f"""
        <div class="weather-visual weather-visual-{tone} weather-{condition_class}" data-weather-condition="{condition}" aria-hidden="true">
          <svg viewBox="0 0 180 150">
            <defs>
              <linearGradient id="sun-{tone}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="{palette["sun_start"]}"/>
                <stop offset="100%" stop-color="{palette["sun_end"]}"/>
              </linearGradient>
              <linearGradient id="cloud-{tone}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="{palette["cloud_start"]}"/>
                <stop offset="100%" stop-color="{palette["cloud_end"]}"/>
              </linearGradient>
              <linearGradient id="storm-{tone}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="{palette["storm_start"]}"/>
                <stop offset="100%" stop-color="{palette["storm_end"]}"/>
              </linearGradient>
              <linearGradient id="rain-{tone}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="{palette["rain_start"]}"/>
                <stop offset="100%" stop-color="{palette["rain_end"]}"/>
              </linearGradient>
              <filter id="soft-{tone}" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="7"/>
              </filter>
              <filter id="shadow-{tone}" x="-35%" y="-35%" width="170%" height="170%">
                <feDropShadow dx="0" dy="10" stdDeviation="8" flood-color="{palette["shadow"]}" flood-opacity=".22"/>
              </filter>
            </defs>
            {scene.format(tone=tone)}
          </svg>
          <div class="visual-temp">{c["current_temp"]}°</div>
        </div>
"""


def _weather_palette(tone: str) -> dict[str, str]:
    palettes = {
        "warm": {
            "sun_start": "#ffbf69",
            "sun_end": "#df7b2f",
            "cloud_start": "#fff2d8",
            "cloud_end": "#f4c887",
            "storm_start": "#8b6f61",
            "storm_end": "#4c4f5a",
            "rain_start": "#4aa7d8",
            "rain_end": "#2878b5",
            "shadow": "#a5672b",
        },
        "action": {
            "sun_start": "#f9d46b",
            "sun_end": "#f59e0b",
            "cloud_start": "#d8f2ff",
            "cloud_end": "#7ed2ff",
            "storm_start": "#7695aa",
            "storm_end": "#264760",
            "rain_start": "#9ee7ff",
            "rain_end": "#38bdf8",
            "shadow": "#06283d",
        },
        "glass": {
            "sun_start": "#7dd3fc",
            "sun_end": "#38bdf8",
            "cloud_start": "#ecfeff",
            "cloud_end": "#bae6fd",
            "storm_start": "#b5b9ff",
            "storm_end": "#64748b",
            "rain_start": "#67e8f9",
            "rain_end": "#7c3aed",
            "shadow": "#4d5f85",
        },
        "minimal": {
            "sun_start": "#43484c",
            "sun_end": "#151a1e",
            "cloud_start": "#f1f2ee",
            "cloud_end": "#b9bfbd",
            "storm_start": "#6b7280",
            "storm_end": "#1f2937",
            "rain_start": "#5f6f7a",
            "rain_end": "#151a1e",
            "shadow": "#1f2930",
        },
        "dashboard": {
            "sun_start": "#9be8ff",
            "sun_end": "#38bdf8",
            "cloud_start": "#c9f1ff",
            "cloud_end": "#5694bd",
            "storm_start": "#6d879b",
            "storm_end": "#1f4058",
            "rain_start": "#b9f4ff",
            "rain_end": "#7dd3fc",
            "shadow": "#061b2c",
        },
    }
    return palettes.get(tone, palettes["warm"])


def _weather_scene(condition: str, condition_class: str) -> str:
    scenes = {
        "clear": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <circle cx="88" cy="72" r="42" fill="url(#sun-{{tone}})" opacity=".18"/>
              <circle cx="88" cy="72" r="30" fill="url(#sun-{{tone}})"/>
              <path d="M88 17v16M88 111v16M33 72h16M127 72h16M49 33l12 12M115 99l12 12M127 33l-12 12M61 99l-12 12" stroke="url(#sun-{{tone}})" stroke-width="6" stroke-linecap="round" opacity=".68"/>
              <path d="M51 118c19 12 55 15 85 0" fill="none" stroke="url(#sun-{{tone}})" stroke-width="4" stroke-linecap="round" opacity=".38"/>
            </g>
""",
        "partly_cloudy": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <circle cx="60" cy="54" r="28" fill="url(#sun-{{tone}})"/>
              <path d="M60 16v13M60 79v13M22 54h13M85 54h13M33 27l9 9M78 72l9 9M87 27l-9 9M42 72l-9 9" stroke="url(#sun-{{tone}})" stroke-width="5" stroke-linecap="round" opacity=".58"/>
              <path d="M69 101c8-18 24-30 45-30 24 0 42 16 47 39 13 3 22 13 22 27 0 16-14 28-31 28H68c-18 0-31-12-31-28 0-14 10-25 25-27 2-3 4-6 7-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3" opacity=".96"/>
              <path d="M79 128c9 11 22 11 31 0 9 11 22 11 31 0" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity=".48"/>
            </g>
""",
        "cloudy": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M36 86c7-15 20-24 37-24 18 0 32 10 39 28 11 2 20 10 23 21 5-3 12-5 19-5 18 0 32 13 32 29 0 17-14 30-33 30H51c-21 0-37-14-37-33 0-17 12-30 29-33-2-5-4-9-7-13z" fill="url(#cloud-{{tone}})" opacity=".72"/>
              <path d="M60 95c8-18 24-30 45-30 25 0 44 17 49 40 15 3 25 15 25 30 0 18-15 31-34 31H60c-20 0-35-13-35-31 0-16 11-28 27-31 2-3 5-6 8-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M66 128h78" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity=".28"/>
            </g>
""",
        "fog": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M59 83c8-16 23-27 43-27 23 0 41 15 46 37 14 3 24 14 24 28 0 17-14 30-32 30H58c-18 0-32-13-32-30 0-15 11-27 27-29 2-3 4-6 6-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3" opacity=".75"/>
              <path d="M35 116h92M52 133h104M29 150h122M64 166h70" stroke="url(#rain-{{tone}})" stroke-width="6" stroke-linecap="round" opacity=".46"/>
            </g>
""",
        "drizzle": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <circle cx="61" cy="48" r="21" fill="url(#sun-{{tone}})" opacity=".92"/>
              <path d="M65 92c8-17 23-28 43-28 23 0 41 16 46 38 14 3 24 14 24 28 0 17-14 30-33 30H62c-19 0-33-13-33-30 0-15 11-27 27-29 2-3 5-6 9-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M73 129c-5 9-8 14-8 18M102 129c-5 9-8 14-8 18M131 129c-5 9-8 14-8 18" stroke="url(#rain-{{tone}})" stroke-width="3" stroke-linecap="round" opacity=".7"/>
            </g>
""",
        "rain": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M58 83c8-16 23-27 43-27 23 0 41 15 47 37 14 3 24 14 24 29 0 17-14 30-33 30H58c-19 0-33-13-33-30 0-15 11-27 27-30 2-3 4-6 6-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M61 129l-11 25M88 129l-11 25M115 129l-11 25M142 129l-11 25" stroke="url(#rain-{{tone}})" stroke-width="5" stroke-linecap="round" opacity=".74"/>
              <path d="M69 166c18 7 50 7 68 0" fill="none" stroke="url(#rain-{{tone}})" stroke-width="4" stroke-linecap="round" opacity=".42"/>
            </g>
""",
        "heavy_rain": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M53 80c9-20 27-33 50-33 27 0 48 18 54 45 17 3 28 17 28 34 0 20-17 36-39 36H55c-22 0-39-15-39-36 0-18 13-32 32-35 1-4 3-8 5-11z" fill="url(#storm-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M55 127l-13 31M80 127l-13 31M105 127l-13 31M130 127l-13 31M155 127l-13 31" stroke="url(#rain-{{tone}})" stroke-width="7" stroke-linecap="round" opacity=".82"/>
              <path d="M55 171c25 9 74 9 99 0" fill="none" stroke="url(#rain-{{tone}})" stroke-width="5" stroke-linecap="round" opacity=".45"/>
            </g>
""",
        "thunderstorm": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M54 79c9-20 27-32 49-32 27 0 47 17 53 43 17 3 29 16 29 34 0 20-17 35-39 35H56c-22 0-39-15-39-35 0-18 13-32 32-35 1-4 3-7 5-10z" fill="url(#storm-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M99 112l-20 35h18l-12 30 36-43h-20l15-22z" fill="url(#sun-{{tone}})" stroke="currentColor" stroke-width="2" opacity=".95"/>
              <path d="M57 132l-10 24M137 132l-10 24" stroke="url(#rain-{{tone}})" stroke-width="5" stroke-linecap="round" opacity=".68"/>
            </g>
""",
        "snow": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M58 83c8-16 23-27 43-27 23 0 41 15 47 37 14 3 24 14 24 29 0 17-14 30-33 30H58c-19 0-33-13-33-30 0-15 11-27 27-30 2-3 4-6 6-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3" opacity=".9"/>
              <path d="M69 132v17M60 141h18M63 135l12 12M75 135l-12 12M111 130v19M101 140h20M104 133l14 14M118 133l-14 14M145 134v15M137 142h16M140 136l11 11M151 136l-11 11" stroke="url(#rain-{{tone}})" stroke-width="3" stroke-linecap="round" opacity=".8"/>
              <path d="M57 169c22-10 70-10 92 0" fill="none" stroke="url(#cloud-{{tone}})" stroke-width="5" stroke-linecap="round" opacity=".72"/>
            </g>
""",
        "sleet": """
            <g class="weather-scene weather-scene-{condition_class}" filter="url(#shadow-{{tone}})">
              <path d="M58 83c8-16 23-27 43-27 23 0 41 15 47 37 14 3 24 14 24 29 0 17-14 30-33 30H58c-19 0-33-13-33-30 0-15 11-27 27-30 2-3 4-6 6-9z" fill="url(#cloud-{{tone}})" stroke="currentColor" stroke-width="3"/>
              <path d="M63 130l-9 22M104 130l-9 22M142 130l-9 22" stroke="url(#rain-{{tone}})" stroke-width="4" stroke-linecap="round" opacity=".68"/>
              <path d="M82 136v16M74 144h16M76 138l12 12M88 138l-12 12M124 137v16M116 145h16M118 139l12 12M130 139l-12 12" stroke="url(#rain-{{tone}})" stroke-width="3" stroke-linecap="round" opacity=".8"/>
            </g>
""",
    }
    return scenes.get(condition, scenes["partly_cloudy"]).format(
        condition_class=condition_class
    )


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
    body { margin: 0; background: var(--weather-page-bg); color: var(--weather-text); font-family: Arial, sans-serif; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 34px 16px; }
    .card { background: var(--weather-surface-bg); border-radius: 32px; padding: 34px; border: 1px solid var(--weather-surface-border); box-shadow: var(--weather-surface-shadow), inset 0 1px 0 rgba(255,255,255,.9); }
    .masthead { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
    .eyebrow { color: var(--weather-label); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; }
    .template-pill { border: 1px solid var(--weather-panel-border); color: var(--weather-label); background: var(--weather-pill-bg); padding: 7px 11px; border-radius: 999px; font-size: 12px; }
    .hero { display: grid; grid-template-columns: minmax(0,1fr) 170px; gap: 22px; align-items: center; margin: 20px 0 22px; border-left: 6px solid var(--weather-accent); background: var(--weather-hero-bg); padding: 22px; border-radius: 26px; box-shadow: inset 0 1px 0 rgba(255,255,255,.78), var(--weather-panel-shadow); }
    h1 { margin: 10px 0 12px; color: var(--weather-heading); font-size: 34px; line-height: 1.2; letter-spacing: -.02em; }
    h2 { margin: 24px 0 12px; color: var(--weather-heading); font-size: 18px; }
    p { margin: 8px 0; line-height: 1.68; }
    .muted { color: var(--weather-muted); font-size: 13px; }
    .weather-visual { color: var(--weather-visual); position: relative; min-height: 140px; display: grid; place-items: center; }
    .weather-visual svg { width: 170px; height: 140px; }
    .visual-temp { position: absolute; right: 4px; bottom: 8px; padding: 7px 13px; background: var(--weather-pill-bg); border-radius: 999px; box-shadow: var(--weather-mini-shadow); font-weight: 800; }
    .action-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .action-card { background: var(--weather-panel-bg); border: 1px solid var(--weather-panel-border); border-radius: 20px; padding: 15px; box-shadow: var(--weather-mini-shadow); }
    .action-clothing { grid-column: 1 / -1; }
    .action-kicker { display: block; color: var(--weather-label); font-size: 12px; font-weight: 700; margin-bottom: 7px; }
    .action-card strong { display: block; line-height: 1.55; color: var(--weather-heading); }
    .period-card { margin-top: 22px; background: var(--weather-panel-soft-bg); border-radius: 22px; padding: 18px; }
    .periods { width: 100%; border-collapse: collapse; font-size: 14px; }
    .periods th, .periods td { border-bottom: 1px solid var(--weather-divider); padding: 12px 4px; text-align: left; }
    .periods th { width: 74px; color: var(--weather-label); }
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
    body { margin: 0; background: var(--weather-page-bg); color: #132432; font-family: Arial, sans-serif; }
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
    .command .weather-visual { color: #b7ecff; position: absolute; right: 16px; bottom: 12px; width: 140px; min-height: 112px; opacity: .88; }
    .command .weather-visual svg { width: 140px; height: 112px; filter: drop-shadow(0 14px 22px rgba(0,0,0,.16)); }
    .command .visual-temp { display: none; }
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
          {_weather_visual(c, "action")}
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
    body { margin: 0; background: var(--weather-page-bg); color: #10243a; font-family: Arial, sans-serif; }
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
    body { margin: 0; background: var(--weather-page-bg); color: #151a1e; font-family: Arial, sans-serif; }
    .wrap { max-width: 690px; margin: 0 auto; padding: 34px 16px; }
    .card { background: #fffffb; border-radius: 0; padding: 42px; border: 1px solid #e4e3dc; box-shadow: 0 18px 56px rgba(31,41,48,.08); }
    .minimal-head { display: grid; grid-template-columns: 1fr auto; gap: 20px; align-items: start; border-bottom: 1px solid #deded6; padding-bottom: 24px; }
    .eyebrow, .muted { color: #6c7478; font-size: 13px; }
    .eyebrow { margin: 0 0 14px; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; }
    .template-pill { color: #444b4f; border: 1px solid #deded6; border-radius: 999px; padding: 7px 11px; font-size: 12px; }
    .minimal-weather { display: flex; justify-content: flex-end; margin: 18px 0 8px; }
    .minimal-weather .weather-visual { color: #2f3437; width: 86px; min-height: 58px; opacity: .42; }
    .minimal-weather .weather-visual svg { width: 86px; height: 72px; }
    .minimal-weather .visual-temp { display: none; }
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
          <div class="minimal-weather">{_weather_visual(c, "minimal")}</div>
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
    body { margin: 0; background: var(--weather-page-bg); color: #17212b; font-family: Arial, sans-serif; }
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
    .card {{ position: relative; }}
    body.weather-clear {{
      --weather-accent: #d98535;
      --weather-page-bg: radial-gradient(circle at 12% 0%, #fff8ec 0, transparent 34%), radial-gradient(circle at 88% 6%, #f3d1a6 0, transparent 36%), linear-gradient(145deg, #f7efe4 0%, #ecd9c0 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(255,250,243,.96) 0%, rgba(255,246,234,.96) 100%);
      --weather-surface-border: rgba(255,255,255,.75);
      --weather-surface-shadow: 0 28px 90px rgba(112,76,38,.24);
      --weather-hero-bg: linear-gradient(135deg, rgba(255,242,218,.92) 0%, rgba(255,233,200,.88) 100%);
      --weather-panel-bg: rgba(255,255,255,.72);
      --weather-panel-soft-bg: rgba(255,255,255,.5);
      --weather-pill-bg: rgba(255,255,255,.78);
      --weather-panel-border: rgba(232,203,166,.7);
      --weather-panel-shadow: 0 18px 46px rgba(159,105,45,.14);
      --weather-mini-shadow: 0 12px 30px rgba(117,78,36,.1);
      --weather-divider: #ead8c1;
      --weather-heading: #3b2f25;
      --weather-text: #2f2b25;
      --weather-muted: #77685a;
      --weather-label: #8a6243;
      --weather-visual: #d98535;
      --weather-glow: rgba(245,158,11,.16);
    }}
    body.weather-partly-cloudy {{
      --weather-accent: #2f8fc9;
      --weather-page-bg: radial-gradient(circle at 10% 0%, #f4fbff 0, transparent 30%), radial-gradient(circle at 90% 4%, #bfe8ff 0, transparent 38%), linear-gradient(145deg, #eff8fc 0%, #dcecf3 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(252,254,255,.96) 0%, rgba(244,250,252,.96) 100%);
      --weather-surface-border: rgba(255,255,255,.78);
      --weather-surface-shadow: 0 28px 90px rgba(45,91,118,.2);
      --weather-hero-bg: linear-gradient(135deg, rgba(231,247,255,.94) 0%, rgba(214,238,249,.88) 100%);
      --weather-panel-bg: rgba(255,255,255,.74);
      --weather-panel-soft-bg: rgba(245,251,253,.74);
      --weather-pill-bg: rgba(255,255,255,.8);
      --weather-panel-border: rgba(181,219,235,.72);
      --weather-panel-shadow: 0 18px 46px rgba(45,91,118,.13);
      --weather-mini-shadow: 0 12px 30px rgba(45,91,118,.1);
      --weather-divider: #cfe3ec;
      --weather-heading: #163248;
      --weather-text: #203744;
      --weather-muted: #607381;
      --weather-label: #3b718d;
      --weather-visual: #2f8fc9;
      --weather-glow: rgba(56,189,248,.14);
    }}
    body.weather-cloudy, body.weather-fog, body.weather-unknown {{
      --weather-accent: #64748b;
      --weather-page-bg: radial-gradient(circle at 18% 0%, #f8fafc 0, transparent 34%), radial-gradient(circle at 88% 8%, #dbe3ea 0, transparent 36%), linear-gradient(145deg, #edf2f5 0%, #d9e1e7 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(250,252,253,.97) 0%, rgba(242,246,248,.97) 100%);
      --weather-surface-border: rgba(255,255,255,.78);
      --weather-surface-shadow: 0 28px 90px rgba(71,85,105,.2);
      --weather-hero-bg: linear-gradient(135deg, rgba(239,244,247,.95) 0%, rgba(223,232,238,.9) 100%);
      --weather-panel-bg: rgba(255,255,255,.72);
      --weather-panel-soft-bg: rgba(247,250,251,.72);
      --weather-pill-bg: rgba(255,255,255,.82);
      --weather-panel-border: rgba(203,213,225,.82);
      --weather-panel-shadow: 0 18px 46px rgba(71,85,105,.12);
      --weather-mini-shadow: 0 12px 30px rgba(71,85,105,.1);
      --weather-divider: #d5dde5;
      --weather-heading: #1f2937;
      --weather-text: #2f3a45;
      --weather-muted: #64717d;
      --weather-label: #64748b;
      --weather-visual: #64748b;
      --weather-glow: rgba(100,116,139,.14);
    }}
    body.weather-drizzle, body.weather-rain, body.weather-heavy-rain, body.weather-sleet {{
      --weather-accent: #0e7490;
      --weather-page-bg: radial-gradient(circle at 12% 0%, #e0f7ff 0, transparent 34%), radial-gradient(circle at 88% 8%, #a9d7ee 0, transparent 38%), linear-gradient(145deg, #e8f4f9 0%, #cddfea 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(248,253,255,.97) 0%, rgba(238,248,252,.97) 100%);
      --weather-surface-border: rgba(226,244,250,.9);
      --weather-surface-shadow: 0 28px 90px rgba(14,82,116,.22);
      --weather-hero-bg: linear-gradient(135deg, rgba(219,242,250,.96) 0%, rgba(203,229,241,.92) 100%);
      --weather-panel-bg: rgba(255,255,255,.76);
      --weather-panel-soft-bg: rgba(242,250,253,.76);
      --weather-pill-bg: rgba(255,255,255,.84);
      --weather-panel-border: rgba(167,216,232,.8);
      --weather-panel-shadow: 0 18px 46px rgba(14,82,116,.14);
      --weather-mini-shadow: 0 12px 30px rgba(14,82,116,.11);
      --weather-divider: #c3dce8;
      --weather-heading: #0f2e44;
      --weather-text: #173242;
      --weather-muted: #557284;
      --weather-label: #25677d;
      --weather-visual: #0e7490;
      --weather-glow: rgba(14,165,233,.16);
    }}
    body.weather-thunderstorm {{
      --weather-accent: #4f46e5;
      --weather-page-bg: radial-gradient(circle at 10% 0%, #dbe4ff 0, transparent 34%), radial-gradient(circle at 92% 8%, #9aa7d8 0, transparent 38%), linear-gradient(145deg, #e5e7f3 0%, #c9cedf 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(249,250,255,.97) 0%, rgba(240,242,249,.97) 100%);
      --weather-surface-border: rgba(232,235,249,.9);
      --weather-surface-shadow: 0 28px 90px rgba(49,46,129,.22);
      --weather-hero-bg: linear-gradient(135deg, rgba(228,231,250,.96) 0%, rgba(211,216,238,.92) 100%);
      --weather-panel-bg: rgba(255,255,255,.76);
      --weather-panel-soft-bg: rgba(246,247,252,.76);
      --weather-pill-bg: rgba(255,255,255,.84);
      --weather-panel-border: rgba(196,202,230,.84);
      --weather-panel-shadow: 0 18px 46px rgba(49,46,129,.14);
      --weather-mini-shadow: 0 12px 30px rgba(49,46,129,.1);
      --weather-divider: #ccd1e4;
      --weather-heading: #1f2437;
      --weather-text: #273044;
      --weather-muted: #626a80;
      --weather-label: #4f46e5;
      --weather-visual: #4f46e5;
      --weather-glow: rgba(79,70,229,.16);
    }}
    body.weather-snow {{
      --weather-accent: #38bdf8;
      --weather-page-bg: radial-gradient(circle at 12% 0%, #ffffff 0, transparent 34%), radial-gradient(circle at 88% 6%, #c9f1ff 0, transparent 38%), linear-gradient(145deg, #f4fcff 0%, #dceff8 100%);
      --weather-surface-bg: linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(247,253,255,.98) 100%);
      --weather-surface-border: rgba(234,248,255,.95);
      --weather-surface-shadow: 0 28px 90px rgba(56,126,158,.18);
      --weather-hero-bg: linear-gradient(135deg, rgba(248,253,255,.98) 0%, rgba(224,246,255,.94) 100%);
      --weather-panel-bg: rgba(255,255,255,.82);
      --weather-panel-soft-bg: rgba(250,254,255,.8);
      --weather-pill-bg: rgba(255,255,255,.88);
      --weather-panel-border: rgba(188,229,245,.82);
      --weather-panel-shadow: 0 18px 46px rgba(56,126,158,.12);
      --weather-mini-shadow: 0 12px 30px rgba(56,126,158,.1);
      --weather-divider: #d0e9f4;
      --weather-heading: #153242;
      --weather-text: #243c48;
      --weather-muted: #607985;
      --weather-label: #2c83a8;
      --weather-visual: #38bdf8;
      --weather-glow: rgba(125,211,252,.18);
    }}
    .card.weather-clear {{ --weather-glow: rgba(245,158,11,.16); }}
    .card.weather-partly-cloudy {{ --weather-glow: rgba(56,189,248,.14); }}
    .card.weather-cloudy, .card.weather-fog, .card.weather-unknown {{ --weather-glow: rgba(100,116,139,.14); }}
    .card.weather-drizzle, .card.weather-rain, .card.weather-heavy-rain, .card.weather-sleet {{ --weather-glow: rgba(14,165,233,.16); }}
    .card.weather-thunderstorm {{ --weather-glow: rgba(79,70,229,.16); }}
    .card.weather-snow {{ --weather-glow: rgba(125,211,252,.18); }}
    .card > * {{ position: relative; z-index: 1; }}
    .card:after {{ content: ""; position: absolute; pointer-events: none; z-index: 0; inset: 18px; border-radius: inherit; box-shadow: 0 0 80px var(--weather-glow, transparent); opacity: .75; }}
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
<body class="weather-{c["current_condition_class"]}">
  <div class="wrap">
    <main class="card weather-{c["current_condition_class"]}" data-email-template="{c["email_template"]}" data-weather-condition="{c["current_condition"]}" aria-label="{escape(c["template_label"])}">
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
