# Weather Morning Report

Standalone Python project for generating an action-oriented personal weather
morning report.

The project is under active development. The initial Python package,
provider-independent weather model, and pytest framework are in place.

- [Design specification](docs/DESIGN.md)
- [Planning transcript](docs/CHAT_TRANSCRIPT.md)

The existing VPS weather scripts and cron jobs are outside this project and
must remain unchanged until a separate deployment decision is approved.

## Development Setup

Python 3.12 or newer is required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

Run the CLI help:

```bash
.venv/bin/weather-report --help
```

Generate a live terminal preview using `wttr.in` with automatic `wttr.is`
fallback:

```bash
.venv/bin/weather-report validate-config
.venv/bin/weather-report preview
```

Configuration can be customized with environment variables documented in
`.env.example`. The `send` command is reserved but is not implemented yet.

Example preview:

```text
主题：[紫外线很强，注意防晒] 天气早报

今日重点：午间紫外线较强
带伞：午间可能有雨，可随手带伞
防晒：UV 10，强烈建议防晒、遮阳，长时间户外注意补涂

穿搭：短袖或薄衬衫即可；避免容易吸水的鞋
```

## Current Structure

```text
src/weather_morning_report/
├── providers/
├── recommendations/
├── rendering/
├── cli.py
├── config.py
├── models.py
└── service.py
tests/
├── test_cli.py
├── test_models.py
├── test_recommendations.py
└── test_wttr_provider.py
```

`models.py` defines the normalized weather data consumed by future
recommendation and rendering modules. Provider implementations must convert
their raw responses into these models before recommendation logic runs.

The normalized model currently covers:

- Location and provider metadata
- Current conditions
- Hourly and daily forecasts
- Optional air quality
- Optional official warnings
- Time-range selection for relevant forecast periods

Models reject naive datetimes, invalid percentages and ranges, unsorted hourly
forecasts, duplicate forecast timestamps, and inconsistent daily temperature
ranges.

## Demo Scope

The current demo implements:

- Environment-backed local configuration
- Live `wttr.in` requests with `wttr.is` fallback
- Provider response normalization
- Commute-aware umbrella guidance
- UV and sunscreen guidance
- Summer-oriented clothing guidance
- Dynamic subject and three key time periods
- Plain-text terminal preview

Caching, HTML email rendering, SMTP delivery, and the `send` command remain
for later Phase 1 work.
