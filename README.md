# Weather Morning Report

[English](README.md) | [简体中文](README.zh-CN.md)

Weather Morning Report generates and emails a concise, action-oriented personal
weather briefing. It highlights whether to carry an umbrella, what to wear,
whether sunscreen is needed, and which parts of the day have meaningful
weather risks.

The application uses `wttr.in` with automatic `wttr.is` fallback, keeps a
freshness-checked local snapshot cache, and sends responsive HTML plus
plain-text email.

## Download

```bash
git clone https://github.com/dengyie/weather-morning-report.git
cd weather-morning-report
```

## Quick Start With Docker

Docker is the recommended deployment method. It requires Docker Engine with
Docker Compose.

```bash
cp .env.example .env
docker compose build
docker compose run --rm report preview
```

Edit `.env` before sending email:

```dotenv
TIMEZONE=Asia/Shanghai
LOCATION_NAME=Changning District, Shanghai
LOCATION_QUERY=Changning,Shanghai

RECIPIENT_NAME=
RECIPIENT_EMAIL=recipient@example.com
ADMIN_EMAIL=admin@example.com
SENDER_EMAIL=sender@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=sender@example.com
SMTP_PASSWORD=replace-me
SMTP_SECURITY=starttls
```

Validate the weather provider and delivery configuration, then send a report:

```bash
docker compose run --rm report validate-config
docker compose run --rm report send
```

Docker Compose stores settings and cached weather data in the persistent
`weather-report-data` volume.

## Docker Settings Page

Delivery settings can also be configured through a browser:

```bash
docker compose up settings
```

Open <http://127.0.0.1:8766>, save the settings, test SMTP, then stop the
container with `Ctrl+C`.

The page is published only on the host loopback address. If using the settings
page, remove the blank `RECIPIENT_*`, `ADMIN_EMAIL`, `SENDER_EMAIL`, and
`SMTP_*` entries from `.env`; environment variables take priority over saved
settings.

## Schedule Docker Delivery

Run the one-shot report container from the host scheduler. For example, on a
host using the `Asia/Shanghai` timezone:

```cron
30 8 * * * cd /opt/weather-morning-report && /usr/bin/docker compose run --rm report send >> /var/log/weather-morning-report.log 2>&1
```

Confirm the host scheduler timezone and complete a manual send before enabling
the schedule. See [Docker deployment](docs/docker-deployment.md) for update and
operation details.

## Native Python Setup

Python 3.12 or newer is required.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

Run commands through the installed CLI:

```bash
.venv/bin/weather-report preview
.venv/bin/weather-report preview --format html > report.html
.venv/bin/weather-report validate-config
.venv/bin/weather-report send
.venv/bin/weather-report settings
```

For a native production installation with a daily systemd timer, follow
[Native systemd deployment](docs/deployment.md).

## Commands

| Command | Purpose |
| --- | --- |
| `weather-report preview` | Fetch weather and render a plain-text report without sending |
| `weather-report preview --format html` | Render the responsive HTML report |
| `weather-report validate-config` | Validate complete delivery settings and provider access |
| `weather-report send` | Generate and send the multipart email |
| `weather-report settings` | Open the local delivery settings page |

`preview` does not require valid SMTP settings. `validate-config` and `send`
require complete delivery settings.

## Reliability

The application queries `wttr.in`, then `wttr.is`. Successful normalized
snapshots are saved atomically.

If both providers fail:

- A cached snapshot no older than `CACHE_MAX_AGE_HOURS` is used and clearly
  labeled.
- If no usable cache exists, no recipient report is sent and the administrator
  receives a failure notification.

## Configuration

Runtime defaults and supported environment variables are documented in
[`.env.example`](.env.example).

- Environment variables override settings saved through the browser page.
- Native settings are stored in `var/settings.json` with permission `600`.
- Docker settings and snapshots are stored in the `weather-report-data` volume.
- `.env`, runtime data, credentials, and generated files are excluded from Git.

## Project Structure

```text
src/weather_morning_report/
├── delivery/          # Email construction and SMTP delivery
├── providers/         # Weather provider contracts and wttr implementation
├── recommendations/   # Period selection and action recommendations
├── rendering/         # HTML and plain-text reports
├── cache.py           # Freshness-checked normalized snapshot cache
├── cli.py             # Command-line interface
├── config.py          # Runtime environment configuration
├── models.py          # Provider-independent weather models
├── service.py         # Application orchestration
├── settings.py        # Delivery settings persistence
└── webui.py           # Local settings page
```

Provider responses are normalized before recommendation and rendering logic
runs. Recommendation thresholds and failure behavior are covered by automated
tests.

## Documentation

- [Current design and behavior](docs/DESIGN.md)
- [Docker deployment](docs/docker-deployment.md)
- [Native systemd deployment](docs/deployment.md)
