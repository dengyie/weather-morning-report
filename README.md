# Weather Morning Report

Standalone Python application that generates and emails an action-oriented
personal weather morning report.

The report prioritizes practical decisions:

- Whether to carry an umbrella
- What to wear
- Whether sunscreen is needed
- Which parts of the day have meaningful weather risks

It uses `wttr.in` with automatic `wttr.is` fallback, a local snapshot cache,
responsive HTML and plain-text email, and a systemd timer for daily delivery.

## Requirements

- Python 3.12 or newer
- Network access to `wttr.in` or `wttr.is`
- SMTP credentials for email delivery

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

Configuration defaults and environment variables are documented in
`.env.example`. Delivery settings may also be stored through the local settings
UI:

```bash
.venv/bin/weather-report settings
```

The UI listens only on `127.0.0.1:8766`. It stores settings in
`var/settings.json` with file permission `600`; saved passwords are never
displayed. Environment variables override stored settings.

## Commands

```bash
.venv/bin/weather-report preview
.venv/bin/weather-report preview --format html > report.html
.venv/bin/weather-report validate-config
.venv/bin/weather-report send
.venv/bin/weather-report settings
```

- `preview` fetches live weather, applies cache fallback when necessary, and
  renders a report without sending email. Missing or invalid delivery settings
  do not block preview generation.
- `validate-config` verifies complete delivery settings and weather-provider
  connectivity.
- `send` generates and sends a multipart HTML and plain-text report.
- `settings` opens the local delivery settings UI.

When `RECIPIENT_NAME` or a stored recipient name is configured, the report uses
it in the greeting. Otherwise, or when delivery settings are invalid, preview
uses a generic greeting. `send` and `validate-config` continue to require valid
delivery settings.

## Reliability

The application queries `wttr.in`, then `wttr.is`. Successful normalized
snapshots are saved atomically to `var/weather_snapshot.json`.

If both providers fail:

- A cached snapshot no older than `CACHE_MAX_AGE_HOURS` is used and clearly
  labeled.
- If no usable cache exists, no recipient report is sent and the administrator
  receives a failure notification.

## Project Structure

```text
src/weather_morning_report/
├── delivery/          # Email construction and SMTP delivery
├── providers/         # Weather provider contracts and wttr implementation
├── recommendations/   # Period selection and action recommendations
├── rendering/         # HTML and plain-text reports
├── cache.py
├── cli.py
├── config.py
├── models.py
├── service.py
├── settings.py
└── webui.py
tests/
deploy/systemd/
docs/
```

Provider responses are normalized before recommendation and rendering logic
runs. Recommendation thresholds are covered by automated tests.

## Deployment

The included systemd timer runs `weather-report send` every day at 08:30
`Asia/Shanghai`, independently of the VPS host timezone.

See [docs/deployment.md](docs/deployment.md) for installation, validation,
logging, and Git-based rollback instructions. The deployment is independent
from any existing weather scripts or cron jobs.

## Design

See [docs/DESIGN.md](docs/DESIGN.md) for the current product behavior,
architecture, and operational constraints.
