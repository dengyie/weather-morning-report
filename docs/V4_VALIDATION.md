# V4 Local Validation

Date: 2026-06-09

## Purpose

This note records the local validation state for the V4 new-user-defaults work.
Runtime data remains intentionally untracked under `var/`.

## Local Test Mailbox

The local SQLite database contains a dedicated test recipient named `mango`.
The actual email address is stored only in ignored local runtime data and should
not be committed to the repository.

Use this recipient for manual delivery checks in local development.

## Validation Performed

- Initialized the local v4 SQLite database and secret key under `var/`.
- Imported legacy local delivery settings from `var/settings.json` into
  `var/weather-report.db`.
- Added the `mango` recipient as the local test mailbox.
- Confirmed the UI health endpoints:
  - `GET /health/live`
  - `GET /health/ready`
- Enqueued a manual morning weather report for the `mango` recipient.
- Confirmed the test mailbox received the weather email.

## Notes

- Do not commit `var/weather-report.db`, `var/secret.key`, `var/settings.json`,
  logs, or backups.
- The local test mailbox and SMTP credentials are environment-specific runtime
  data, not source-controlled fixtures.
