# Phase 11 Real SMTP Transport Design

> Status: proposed and implemented on `codex/phase-11-real-smtp-transport`.
> Scope: Phase 11 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: dashboard auth, encrypted password storage, external provider OAuth, queue worker daemonization, and OpenPet-owned secret management.

## Goal

Phase 11 activates a real SMTP transport for service-backed Email delivery while preserving deterministic fake transports for tests and keeping SMTP secrets out of persisted JSON, HTTP responses, logs, and delivery history.

## Design

- Add `nodemailer` as the production SMTP client dependency.
- Keep `sendEmailNow` responsible for recipient lookup, report rendering, history records, and redacted error handling.
- Add a focused SMTP transport module that maps service configuration to nodemailer options:
  - `plain`: `secure: false`, `ignoreTLS: true`;
  - `starttls`: `secure: false`, `requireTLS: true`;
  - `ssl`: `secure: true`.
- Read SMTP password from `env.SMTP_PASSWORD`; do not persist raw passwords in `configuration.json`.
- Treat `configuration.smtp.passwordSaved` as an indicator that the runtime expects `SMTP_PASSWORD` to be present.
- Fail clearly when SMTP host, sender identity, or required password is missing.
- Default `createServiceApp` to the real SMTP transport, while keeping `emailTransport` injection for tests.
- Preserve fake transport behavior for unit tests and service route tests.
- Add timeout support through `SMTP_TIMEOUT_MS`, defaulting to 10000 ms.

## Verification

Required gates:

- SMTP transport tests for security mapping, auth mapping, timeout mapping, and missing configuration.
- Service route test proving default send-now uses the real transport factory when no fake transport is injected.
- Existing fake transport send-now tests remain green.
- Full phase gate after production review.
