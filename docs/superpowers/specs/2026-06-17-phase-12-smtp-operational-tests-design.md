# Phase 12 SMTP Operational Tests Design

> Status: proposed and implemented on `codex/phase-12-smtp-operational-tests`.
> Scope: Phase 12 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: dashboard authentication, encrypted SMTP password storage, scheduler worker daemonization, provider OAuth, and OpenPet-owned secret management.

## Goal

Phase 12 adds dashboard/service operations for SMTP test connection and test Email so users can verify their mail configuration before relying on send-now or scheduled delivery.

## Design

- Extend the SMTP transport with `verify(message)` that validates configuration, builds the same nodemailer options as send, and calls the SMTP client's `verify()`.
- Add `POST /configuration/smtp/test-connection`:
  - loads current configuration;
  - runs `emailTransport.verify({ smtp, envelope })`;
  - returns `{ ok: true, status: "connected" }` on success;
  - returns a redacted 502 JSON response on failure.
- Add `POST /email/test`:
  - requires a known recipient id;
  - sends a short operational test Email through the configured transport;
  - includes SMTP config in the transport message;
  - does not create `delivery-history.json` records.
- Add configuration page controls for both actions.
- Keep runtime password material in `SMTP_PASSWORD`; do not persist submitted password values.
- Preserve existing fake transport injection and existing send-now behavior.

## Verification

Required gates:

- SMTP transport verify test.
- Service route tests for test connection success and redacted failure.
- Service route test for test Email success without delivery history.
- Configuration page test for operational controls.
- Full phase gate after production review.
