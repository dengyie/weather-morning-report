# Version History

This document summarizes the product milestones from V1 through V5 so new
contributors can quickly understand why the project looks the way it does.

The versions below are development milestones, not all published package
versions. The latest published installable package may lag behind the newest
development milestone.

## At a Glance

| Milestone | Theme | Main user-facing change | Runtime model |
| --- | --- | --- | --- |
| V1 | Weather report demo | Generate an action-oriented forecast preview | One-shot CLI |
| V2 | Reliable email delivery | Send personalized reports to one or many recipients | CLI, scheduler, local settings UI |
| V3 | Self-hosted service foundation | Admin UI, SQLite configuration, worker queue, backups | Long-running UI + worker |
| V4 | Faster new-user setup | Defaults for future recipients and local validation record | V3 service with setup defaults |
| V5 | Configuration workbench and email templates | More efficient administration UI, recipient template choices, weather-aware HTML email visuals | V3/V4 service with refreshed UI |

## V1: Weather Report Demo

V1 established the core product idea: turn raw forecast data into advice that
can be understood in a few seconds.

Key capabilities:

- Fetch weather from the wttr JSON API.
- Normalize provider data into project-owned weather models.
- Generate action-oriented guidance for umbrella, clothing, sunscreen, and
  meaningful weather risks.
- Render a plain-text preview through the CLI.
- Cover recommendation and provider parsing behavior with automated tests.

Important files:

- `src/weather_morning_report/providers/`
- `src/weather_morning_report/recommendations/`
- `src/weather_morning_report/rendering/text.py`
- `src/weather_morning_report/service.py`
- `src/weather_morning_report/cli.py`

## V2: Reliable CLI Delivery

V2 made the demo deployable for daily personal use and small recipient groups.
This is the line represented by the `v0.2.0` release tag.

Key capabilities:

- Weather snapshot cache with freshness checks and fallback behavior.
- Responsive HTML report rendering alongside plain text.
- SMTP delivery with multipart email messages.
- Administrator failure notifications when provider data cannot be used.
- Local browser settings page for delivery settings.
- Multiple recipients, each with independent name, email, location name, and
  provider query.
- Location grouping so a shared location is fetched once per send.
- Docker deployment, native systemd deployment, and release artifacts.

Important files:

- `src/weather_morning_report/cache.py`
- `src/weather_morning_report/delivery/`
- `src/weather_morning_report/rendering/html.py`
- `src/weather_morning_report/settings.py`
- `src/weather_morning_report/webui.py`
- `compose.yaml`
- `deploy/systemd/`

Related documentation:

- `docs/DESIGN.md`
- `docs/docker-deployment.md`
- `docs/deployment.md`

## V3: Self-Hosted Service Foundation

V3 is the breaking service redesign. It changes the project from a one-shot CLI
plus temporary settings page into a self-hosted service with a durable admin UI
and a separate worker.

Key capabilities:

- FastAPI administration UI with login, sessions, lockout, logout, and
  local CLI password reset.
- SQLite as the source of truth for recipients, schedules, SMTP settings,
  provider settings, branding, notifications, jobs, run history, and backups.
- Alembic migrations and compatibility checks for schema/task protocol.
- External secret-key file for encrypted SMTP and future provider credentials.
- Long-running worker with a single-worker lease, queue claiming, retry state,
  deduplication, and durable `dispatching` handling.
- Manual report preview with confirmation before enqueueing a send job.
- Backup creation, retention, and dashboard download.
- Explicit setup, upgrade, restore, and admin CLI commands.

Important files:

- `src/weather_morning_report/ui.py`
- `src/weather_morning_report/worker.py`
- `src/weather_morning_report/jobs.py`
- `src/weather_morning_report/v3_service.py`
- `src/weather_morning_report/database/`
- `src/weather_morning_report/migrations/`
- `src/weather_morning_report/templates/`

Related documentation:

- `docs/V3_ARCHITECTURE.md`

Known V3 target gaps are tracked in `docs/V5_DEVELOPMENT.md` because the V5 UI
review re-checked the current implementation against the V3 target architecture.

## V4: New-User Defaults

V4 focuses on reducing setup friction after the service foundation is in place.
It adds configurable defaults for future recipients and schedules.

Key capabilities:

- `new_user_defaults` SQLite singleton.
- Default location, provider query, timezone, language, send time, report type,
  send policy, and enabled state for newly created recipients.
- Automatic default schedule creation when a new recipient is added.
- Configuration UI controls for editing those defaults.
- Local validation record for the real development mailbox and SMTP flow.

Important files:

- `src/weather_morning_report/migrations/versions/0003_new_user_defaults.py`
- `src/weather_morning_report/configuration.py`
- `src/weather_morning_report/templates/configuration.html`

Related documentation:

- `docs/V4_VALIDATION.md`

## V5: Configuration Workbench and Email Templates

V5 improves the administration experience after configuration grew beyond a
single stacked settings page. It also upgrades the HTML email presentation layer
so different recipients can use different visual templates while sharing the
same report data and delivery path. It keeps the server-rendered FastAPI/Jinja
model and does not introduce a separate frontend stack.

Key capabilities:

- Configuration center redesigned as a workbench with left-side navigation.
- Higher-density recipient editing cards and schedule table-style rows.
- Light weather-inspired visual treatment while preserving professional admin
  clarity.
- Static browser preview at `docs/ui-preview/configuration.html`.
- Visible UI milestone labels updated to `Weather Morning Report v5`.
- Recipient email-template preferences surfaced in the recipient workflow.
- Five named atmosphere templates: warm, action, glass gradient, minimal, and
  dashboard.
- Template `1` remains the default for new recipients and unknown template
  values.
- Weather-aware HTML templates with condition-specific palettes and inline SVG
  scenes for clear, cloudy, fog, rain, heavy rain, thunderstorm, snow, sleet,
  and unknown conditions.
- UI coverage check for login, dashboard, configuration, manual preview,
  manual enqueue, backup download, and archive/restore flows.

Important files:

- `src/weather_morning_report/templates/configuration.html`
- `src/weather_morning_report/static/app.css`
- `src/weather_morning_report/rendering/html.py`
- `docs/ui-preview/configuration.html`
- `src/weather_morning_report/email_templates.py`
- `src/weather_morning_report/migrations/versions/0004_recipient_email_preferences.py`

Related documentation:

- `docs/V5_DEVELOPMENT.md`

## Current Contributor Map

Start here when changing each area:

- Report logic: `recommendations/`, `rendering/`, `models.py`
- Legacy CLI delivery: `service.py`, `settings.py`, `webui.py`, `delivery/`
- V3+ service UI: `ui.py`, `templates/`, `static/app.css`
- V3+ worker: `worker.py`, `jobs.py`, `v3_service.py`
- Database and migrations: `database/`, `migrations/versions/`
- Deployment: `compose.yaml`, `Dockerfile`, `deploy/systemd/`, `docs/deployment.md`

## Validation Checklist

Before merging milestone-level changes:

- Run `python -m pytest` from the project virtual environment.
- For UI changes, log in through the FastAPI UI and check dashboard,
  configuration, manual preview, and enqueue flows.
- For delivery changes, use the local `mango` test recipient documented in
  `docs/V4_VALIDATION.md` when a real SMTP send is required.
- Never commit runtime data under `var/`, secret keys, local mailbox addresses,
  logs, or generated backups.
