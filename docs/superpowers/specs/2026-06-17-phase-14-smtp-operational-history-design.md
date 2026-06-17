# Phase 14 SMTP Operational History Design

> Status: proposed on `codex/phase-14-smtp-operational-history`.
> Scope: Phase 14 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: encrypted SMTP password storage, scheduler daemonization, full SQLite migration, provider OAuth, and OpenPet-owned secret management.

## Goal

Phase 14 makes SMTP operational checks auditable by persisting bounded, redacted operational history and surfacing the most recent checks in the configuration page.

## Design

- Add a dedicated service-owned SMTP operational history store under `OPENPET_DATA_DIR`, separate from weather report delivery history.
- Persist records for:
  - SMTP connection test success/failure;
  - test Email success/failure.
- Record only operationally useful fields such as timestamp, action type, status, recipient summary when relevant, message id when relevant, and redacted error text when relevant.
- Keep runtime SMTP secrets out of persisted operational history.
- Render a recent SMTP operational history section in the configuration page's SMTP card area.
- Preserve existing send-now delivery history behavior and existing JSON/page-mode SMTP operational route contracts.

## Verification

Required gates:

- storage tests for bounded SMTP operational history;
- service route tests proving both SMTP operational actions append history on success and failure;
- configuration page tests proving recent SMTP operational history is rendered;
- regression checks proving delivery history remains unchanged for weather report sends and separate from SMTP operational history;
- full phase gate after production review.
