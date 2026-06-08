# Weather Morning Report

[English](README.md) | [简体中文](README.zh-CN.md)

Weather Morning Report is a self-hosted weather briefing and delivery service.
It turns forecast data into concise, action-oriented advice: whether to carry
an umbrella, what to wear, whether sunscreen is needed, and which parts of the
day have meaningful weather risks.

It can send a private daily report to yourself, or deliver personalized reports
to family members, teammates, subscribers, or anyone who needs them. Each
recipient can have an independent name, email address, and weather location.
Recipients in the same location share one weather fetch, while every person
receives a separate personalized email without exposing the other recipients.

The current provider is `wttr.in` with automatic `wttr.is` fallback. The
provider-independent architecture is designed to support configurable weather
APIs in a future release. The application also keeps freshness-checked,
location-specific snapshot caches and sends responsive HTML plus plain-text
email.

## Download and Install

Download the latest wheel or source archive from
[GitHub Releases](https://github.com/dengyie/weather-morning-report/releases/latest).
Install a downloaded wheel with Python 3.12 or newer:

```bash
python3.12 -m pip install ./weather_morning_report-*.whl
weather-report --help
```

You can also install a tagged release directly from GitHub:

```bash
python3.12 -m pip install \
  git+https://github.com/dengyie/weather-morning-report.git@v0.2.0
```

To develop or deploy with Docker, clone the repository:

```bash
git clone https://github.com/dengyie/weather-morning-report.git
cd weather-morning-report
```

This is a Python application, so it is not distributed through npm. Publishing
the same package to PyPI is planned; GitHub Release wheels provide the standard
Python installation experience today.

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
# For multiple recipients, use one-line JSON and remove the legacy fields above:
# RECIPIENTS_JSON=[{"name":"Alice","email":"alice@example.com","location_name":"Shanghai","location_query":"Shanghai"}]
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

The page is published only on the host loopback address. It supports multiple
recipients and an independent location for each person. If using the settings
page, remove the blank `RECIPIENT_*`, `RECIPIENTS_JSON`, `ADMIN_EMAIL`,
`SENDER_EMAIL`, and `SMTP_*` entries from `.env`; environment variables take
priority over saved settings.

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
- `RECIPIENTS_JSON` configures multiple recipients and their locations.
- Legacy `RECIPIENT_NAME` and `RECIPIENT_EMAIL` remain supported for one
  recipient using the default `LOCATION_NAME` and `LOCATION_QUERY`.
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

## Roadmap

- Configurable weather API providers and credentials
- Additional provider-backed weather warnings and air-quality data
- More scheduling and recipient segmentation options

## v3 Development Foundation

The approved breaking v3 service architecture is documented in
[docs/V3_ARCHITECTURE.md](docs/V3_ARCHITECTURE.md). Its SQLite, Alembic,
external-key encryption, administrator authentication, configuration center,
job queue, scheduler, retry state machine, and single-worker lease are under
development alongside the still-operational v0.2 commands. The worker creates
idempotent SQLite Online Backup API snapshots and retains seven daily plus four
weekly backups. Authenticated operators can download them from the dashboard;
the external secret key must be backed up separately.

Automatic delivery switches to a durable `dispatching` state before SMTP is
called. If the worker stops during that window, automatic resend is suppressed
and the result is marked unknown to avoid duplicate mail. Restoring without the
original external key generates a replacement key and clears encrypted
credentials so they can be entered again.

Initialize a new v3 data directory interactively:

```bash
WEATHER_REPORT_DB_PATH=var/weather-report.db \
WEATHER_REPORT_SECRET_KEY_FILE=var/secret.key \
.venv/bin/weather-report setup
```

Database maintenance and local administrator commands:

```bash
.venv/bin/weather-report setup upgrade
.venv/bin/weather-report setup restore /path/to/weather-report.db
.venv/bin/weather-report admin reset-password
.venv/bin/weather-report serve-ui
.venv/bin/weather-report serve-worker
```

These commands use only the deployment-level `WEATHER_REPORT_DB_PATH` and
`WEATHER_REPORT_SECRET_KEY_FILE` environment variables. Business configuration
will move into SQLite as the v3 UI and worker are implemented.

The v3 Docker Compose stack uses separate long-running UI and worker services:

```bash
docker compose run --rm setup
docker compose up -d ui worker
```

The UI is published only at <http://127.0.0.1:8766>; the worker exposes no
network port.

## Documentation

- [Current design and behavior](docs/DESIGN.md)
- [Approved v3 architecture](docs/V3_ARCHITECTURE.md)
- [Docker deployment](docs/docker-deployment.md)
- [Native systemd deployment](docs/deployment.md)
