# Phase 4 Web Dashboard Conservative Migration Design

> Status: proposed for implementation after review approval.
> Scope: Phase 4 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: Email delivery, SMTP transport, scheduler worker, unified extension package, OpenPet core changes, full visual redesign.

## Goal

Phase 4 promotes the recovered legacy dashboard, configuration workbench, and manual preview workflows into active JavaScript/Fastify service views without depending on Python or Jinja.

The implementation should preserve the legacy information architecture first, then leave room for later visual modernization.

## Product Direction

Use a conservative migration path:

- keep the recovered dashboard, configuration, and manual preview workflows recognizable;
- port templates into active `templates/web/` or equivalent JS view modules;
- use active `static/app.css` for the dashboard visual system;
- keep forms local-first and service-owned;
- add validation for the configuration domains listed in the migration design;
- avoid introducing login/forgot-password pages until dashboard auth mode is decided.

This follows the migration document's instruction to preserve dashboard/workbench/manual-preview workflows before adding new UI concepts.

## Active Pages

Phase 4 should add these active service routes:

| Route | Purpose |
| --- | --- |
| `GET /` | Dashboard home/status with service state, manual preview entry, run history empty state or summary, and links to configuration/logs. |
| `GET /configuration` | Full configuration workbench for defaults, recipients, schedules, SMTP, providers, branding, and notifications. |
| `POST /configuration/defaults` | Validate and save default recipient/report settings. |
| `POST /configuration/recipients` | Validate and create or update recipients. |
| `POST /configuration/schedules` | Validate and create or update schedules. |
| `POST /configuration/smtp` | Validate and save SMTP connection metadata without echoing saved passwords. |
| `POST /configuration/branding` | Validate and save report branding settings. |
| `POST /configuration/notifications` | Validate and save notification/retention settings. |
| `POST /manual/preview` | Generate a local manual preview confirmation page from current weather/report inputs. |
| `GET /logs` | Show recent service log lines or an empty state if no log file exists. |

Archive/restore actions can be deferred unless needed to preserve editable local workflow parity in the first pass.

## Data And Storage

Use JSON files in `OPENPET_DATA_DIR` for Phase 4, with clear boundaries that allow a later SQLite migration.

Recommended active files:

- `configuration.json` for defaults, recipients, schedules, SMTP metadata, providers, branding, and notifications;
- `manual-previews.json` or an in-memory preview token map only if preview confirmation needs short-lived state;
- `service.log` remains in `OPENPET_LOG_DIR`.

The storage module should provide focused functions instead of exposing raw file access to route handlers:

- `loadConfiguration(paths)`;
- `saveConfiguration(paths, configuration)`;
- `createDefaultConfiguration()`;
- `readRecentLogs(paths, limit)`.

SMTP password handling for Phase 4 should be conservative:

- accept a new password field;
- store only a redacted saved marker or omit persistent password storage until the Email phase defines encryption/secrets;
- never render a stored secret value back into HTML.

## Validation

Validation should live in a service configuration module, not in view templates.

Minimum rules:

- recipient name, email, location name, location query, timezone, and language are required;
- recipient email must contain a single `@` with non-empty local and domain parts;
- schedule recipient id must refer to an existing non-archived recipient;
- schedule time must match `HH:MM`;
- report type must be `morning`, `midday`, or `evening`;
- send policy must be `always` or `changes_only`;
- SMTP port must be an integer between 1 and 65535;
- SMTP security must be `starttls`, `ssl`, or `plain`;
- branding accent color must match `#RRGGBB`;
- retention days and alert cooldown must be non-negative integers.

Validation errors should render back into the relevant page with user-safe messages and no secret echo.

## Rendering

Prefer small JS rendering modules over a new templating dependency for Phase 4.

Suggested files:

- `service/views/layout.js` owns shared HTML shell, navigation, escaping helpers, and page chrome;
- `service/views/dashboard.js` renders dashboard home;
- `service/views/configuration.js` renders the configuration workbench;
- `service/views/manual-preview.js` renders manual preview confirmation;
- `service/views/logs.js` renders log view.

Every user-controlled string must be HTML-escaped before rendering.

## Testing

Use TDD for implementation.

Required tests:

- `GET /configuration` renders active HTML without Jinja markers such as `{%` or `{{`;
- `POST /configuration/recipients` rejects invalid email and preserves safe form values;
- `POST /configuration/recipients` accepts a valid recipient and persists it in `OPENPET_DATA_DIR`;
- `POST /configuration/schedules` rejects unknown recipient ids;
- `POST /configuration/smtp` does not echo submitted password in response or saved display fields;
- `POST /configuration/branding` rejects invalid accent color;
- `POST /manual/preview` renders a confirmation page without sending Email;
- `GET /logs` renders recent log lines without failing when the log file is missing;
- dashboard routes continue to serve active CSS.

Existing command-plugin package tests must keep passing. Current `.openpet-plugin.zip` should remain command-only until the unified extension package phase.

## Review And Release Gates

Before Phase 4 is committed:

1. Run the local verification suite: `npm ci`, `npm test`, `npm run build`, `npm run lint`, `npm run typecheck`, `npm run package:plugin`, and `git diff --check`.
2. Use `production-code-quality-review` on the Phase 4 diff.
3. Fix confirmed findings.
4. Update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` with the Phase 4 development record.
5. Commit to a `codex/phase-4-web-dashboard` branch, push, and open a draft PR.

## Open Decisions

- Dashboard auth remains out of Phase 4 unless a local token gate is required before exposing settings routes.
- SQLite remains deferred until Email delivery or scheduler behavior requires leases, retries, and delivery history transactions.
- Visual redesign remains deferred; this phase preserves workflow and safety first.
