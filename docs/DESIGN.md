# Weather Morning Report Design

Status: Implemented
Language: Python 3.12+
Delivery schedule: 08:30 Asia/Shanghai

This document describes the currently implemented v0.2 architecture. The
approved breaking redesign for the future v3.0 service is documented in
[V3_ARCHITECTURE.md](V3_ARCHITECTURE.md).

## Product Goal

Generate concise personalized weather reports that communicate useful actions
within ten seconds. Reports may be sent to one person or to multiple
recipients, each with an independent email address and weather location:

- Whether to carry an umbrella
- What to wear
- Whether sunscreen is needed
- Whether commute or daytime activities face meaningful weather risks

The report uses calm, direct language. High-impact weather takes priority over
the normal greeting and comfort advice.

## Report Behavior

Recommendations cover 07:00-22:00 and show three relevant periods.

Workdays use:

- Morning commute: 07:00-10:00
- Midday: 11:00-14:00
- Evening commute: 17:00-20:00

Weekends use:

- Morning: 08:00-11:00
- Afternoon: 12:00-17:00
- Evening: 18:00-22:00

The subject contains one highest-priority action. The body contains the primary
focus, umbrella guidance, sunscreen guidance, clothing advice, three period
summaries, current conditions, daily temperature range, and a short closing.
When a recipient name is configured, it is used only in the greeting. Each
recipient receives an individual email; addresses are never exposed to other
recipients.

## Recommendation Priorities

Subject and focus priority:

1. Thunderstorm or heavy rain
2. Strong wind
3. Dangerous heat
4. Rain during primary outing periods
5. Hot conditions
6. Strong UV
7. Midday rain
8. Comfortable conditions

Umbrella advice emphasizes primary outing periods and becomes a softer reminder
for midday-only rain. Sunscreen advice uses graded UV thresholds. Clothing
advice combines feels-like temperature, humidity, rain risk, and wind.

Thresholds live in the recommendation module and are covered by automated
tests.

## Data and Reliability

The primary source is the `wttr.in` JSON API. `wttr.is` is queried when the
primary source fails. Raw provider responses are converted into a normalized
weather snapshot before recommendation or rendering.

Successful snapshots are saved atomically. If all live providers fail, a cached
snapshot may be used only while it is within the configured freshness limit,
which defaults to 12 hours. Cached reports display their data time.

Batch delivery groups recipients by location. Each location is fetched once
per run and uses an independent cache file.

Cache schema v1 remains rollback-compatible. New snapshots continue writing the
legacy `location.latitude`, `location.longitude`, `air_quality`, and `warnings`
fields with empty values so the previous application version can read snapshots
written before a rollback. The current reader ignores those compatibility
fields.

If live providers fail and no valid cache exists, the application does not send
recipient-facing advice. It sends an administrator-only failure notification.

## Architecture

```text
weather_morning_report/
├── providers/         # Fetch and normalize weather data
├── recommendations/  # Select periods and generate advice
├── rendering/         # Render HTML and plain text
├── delivery/          # Construct and send email
├── cache.py           # Persist normalized snapshots
├── config.py          # Environment-backed runtime configuration
├── settings.py        # Delivery settings and secure persistence
├── webui.py           # Local-only settings interface
├── service.py         # Application orchestration
└── cli.py             # Command-line interface
```

Supported commands:

```text
weather-report preview
weather-report preview --format html
weather-report send
weather-report validate-config
weather-report settings
```

`preview` depends only on weather configuration. It may use `RECIPIENT_NAME` or
the stored recipient name, but malformed settings files and invalid SMTP
settings must not block preview generation; they silently fall back to the
generic greeting. `send` and `validate-config` strictly validate complete
delivery settings.

Delivery settings support the legacy single recipient fields and a recipient
list containing name, email, location display name, and provider query. Future
weather API credentials will be added at the provider configuration boundary,
without changing recommendation or rendering modules.

## Security and Operations

- No real names, email addresses, credentials, production `.env` files, or
  runtime snapshots are committed.
- Local settings and cache files live under ignored `var/`.
- Stored settings use file permission `600`.
- The settings UI defaults to `127.0.0.1` and uses a per-process CSRF token.
  Docker listens inside the container on `0.0.0.0`, while Compose publishes it
  only on the host loopback address.
- Email is multipart HTML and plain text with no JavaScript, remote assets, or
  tracking pixels.
- The systemd service writes only to the runtime `var/` directory.
- This project does not modify unrelated VPS scripts or cron jobs.

## Acceptance Criteria

- Provider fallback and cache freshness behavior are tested.
- Multiple recipients, per-recipient locations, grouped weather fetches, and
  address privacy are tested.
- Umbrella, UV, clothing, severe-weather, workday, and weekend rules are tested.
- HTML and plain-text reports remain readable and use the configured greeting.
- Preview remains available when delivery settings are missing or invalid.
- SMTP settings, delivery, and administrator failure notification are tested.
- Schema v1 snapshots remain readable after rolling back one application
  version.
- CLI configuration errors are reported without tracebacks.
- Repository scanning finds no secrets, real personal data, or generated
  runtime files.
