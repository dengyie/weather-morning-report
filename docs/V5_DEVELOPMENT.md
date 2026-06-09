# V5 Configuration Workbench and Email Template Development

Date: 2026-06-09

## Purpose

V5 records the administration UI refresh that turns the configuration center
from a long stacked settings page into a more efficient workbench. It also
records the richer HTML email presentation layer that lets different recipients
use different visual templates without coupling templates to weather data.

The V5 work keeps the existing FastAPI/Jinja server-rendered architecture and
does not add a frontend build pipeline.

## Scope

V5 covers:

- A professional configuration workbench layout with a persistent left-side
  navigation rail.
- Higher-density recipient and schedule editing patterns for daily operation.
- A light weather-inspired visual treatment for the configuration hero and
  sidebar summary.
- A static design preview at `docs/ui-preview/configuration.html` for direct
  browser review without running the server.
- Visible UI version labels updated to `Weather Morning Report v5`.
- A recipient-level email template preference, defaulting to template `1`.
- Five email atmosphere templates:
  - `1` / `暖调风格`
  - `2` / `行动风格`
  - `3` / `玻璃渐变`
  - `4` / `极简风格`
  - `5` / `仪表风格`
- Weather-aware HTML presentation: each template keeps the same report data but
  can render condition-specific colors and inline SVG weather visuals.

Related configuration already present in the service is surfaced in the V5 UI,
including recipient email-template preferences.

## Email Template Layer

The V5 email renderer treats templates as a presentation layer over a stable
report context. Weather data, recommendation text, and delivery logic remain
shared; template selection only changes visual composition.

Implementation details:

- `src/weather_morning_report/email_templates.py` owns the template option list,
  labels, default value, and normalization.
- `render_html(..., email_template=...)` normalizes the selected template and
  falls back to template `1` for unknown values.
- The V3+ service stores recipient preferences in
  `recipient_email_preferences` and reads them when rendering previews or
  queued report emails.
- The renderer emits `data-email-template` and `data-weather-condition`
  attributes for easier inspection and regression testing.
- Weather condition classes are applied to `<body>` and the card container so
  the same template can shift its palette for clear, cloudy, rainy, stormy,
  snowy, and unknown conditions.

Presentation rules:

- Only clear weather keeps the warm yellow page palette.
- Rain, drizzle, heavy rain, and sleet use cooler blue palettes.
- Cloudy, fog, and unknown conditions use neutral gray-blue palettes.
- Thunderstorm uses a deeper indigo palette.
- Snow uses a bright ice-blue palette.
- Weather icons are inline SVG scenes, not external image assets, so the emails
  remain self-contained and compatible with modern mail clients.
- The richer visuals are added without allowing administrators to edit raw HTML
  or executable templates.

## Design Principles

The V5 UI follows the `ui-ux-pro-max` priority order:

1. Accessibility first: visible labels, keyboard focus states, skip link, and
   non-color-only status text.
2. Interaction targets stay at least 44px tall for primary controls.
3. Layout remains responsive: desktop uses sidebar + workbench; narrow screens
   collapse to a single column.
4. Style is intentionally restrained: professional SaaS admin structure, compact
   workbench density, and light weather texture only where it helps hierarchy.
5. Forms keep stable server-rendered contracts: field names, actions, CSRF
   tokens, archive/restore URLs, and POST behavior remain unchanged.
6. Email templates follow the same data contract: visual style is configurable,
   but report meaning and delivery behavior are not duplicated per template.

## UI Coverage Checked

The current UI exposes the core documented service functions:

- Login, forgot-password instructions, logout, and logout-all.
- Dashboard status cards for database, worker, and queue.
- Manual report preview and explicit enqueue confirmation.
- Recent run history on the dashboard.
- Backup list and database-backup download action.
- Configuration workbench for new-user defaults, recipients, locations,
  timezones, languages, email templates, schedules, SMTP, providers, branding,
  webhooks, notification retention, and secret-key backup confirmation.
- Recipient and schedule archive/restore flows.
- Health endpoints: `/health/live` and `/health/ready`.

## Validation

Validated locally on 2026-06-09:

- Sent a real manual morning report to the local `mango` test mailbox through
  the v4/v5 SQLite queue and worker path.
- Confirmed the resulting manual job and run history rows were marked `sent`.
- Ran the full automated test suite successfully:
  `166 passed, 1 warning`.
- Ran a temporary-database UI reachability probe covering login, dashboard,
  configuration, archived configuration view, manual preview, manual enqueue,
  backup download, and schedule archive/restore.
- Added renderer coverage for condition-specific SVG scenes, template weather
  visual inclusion, cool rainy palettes, and non-clear weather avoiding the
  clear/warm page colors.

The remaining warning is the existing Starlette `httpx2` deprecation warning.

## Known Gaps

The V5 refresh does not complete every target listed in
`docs/V3_ARCHITECTURE.md`. Remaining UI gaps:

- Dashboard does not yet show detailed UI/worker component versions or
  schema/task-protocol compatibility metadata.
- Dashboard does not yet show a complete today-schedule or next-send view.
- Run history does not yet support filtering by recipient, date, report type,
  or status, and does not yet include an immediate cleanup action.
- Retry actions are not yet exposed as explicit UI controls.
- Recent provider/SMTP error panels and old cron/systemd conflict warnings are
  not yet fully implemented.
- UI language selection is not exposed; the administration UI remains primarily
  Chinese.

## Notes

- Runtime data under `var/` remains intentionally untracked.
- `APPLICATION_VERSION` and schema metadata are not bumped by this document;
  this file records the UI development milestone, not a database protocol
  change.
