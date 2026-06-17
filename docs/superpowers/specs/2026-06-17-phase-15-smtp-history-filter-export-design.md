# Phase 15 SMTP Operational History Filter/Export Design

> Status: proposed on `codex/phase-15-smtp-history-filter-export`.
> Scope: Phase 15 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: encrypted SMTP password storage, scheduler daemonization, full SQLite migration, provider OAuth, and OpenPet-owned secret management.

## Goal

Phase 15 makes SMTP operational history easier to use by adding conservative filtering in the configuration page and service-owned filtered export endpoints for audit and support workflows.

## Design

- Keep the existing SMTP operational history file and bounded retention behavior from Phase 14.
- Add filter support for:
  - action type: `all`, `test-connection`, `test-email`;
  - status: `all`, `connected`, `sent`, `failed`;
  - recipient id: `all` or a known recipient id.
- Render a small filter form above the SMTP operational history list in the configuration page.
- Reflect the current filter state in query parameters so filtered pages are shareable and export actions preserve the same scope.
- Add filtered export endpoints under the service:
  - `GET /configuration/smtp/history/export?format=json`
  - `GET /configuration/smtp/history/export?format=csv`
- Export only redacted service-owned SMTP operational history fields already safe to persist.
- Preserve existing SMTP operational history rendering, JSON/page-mode SMTP operational route behavior, and delivery-history separation.

## Filter Semantics

- Missing or invalid filter values should fall back to `all`.
- Recipient filters should match stored `recipientId`.
- Records without a recipient, such as SMTP connection tests, should remain visible when recipient filter is `all` and be excluded when a specific recipient id is selected.
- Filter order should preserve newest-last storage ordering; page rendering may still reverse for newest-first display if current UI keeps that behavior.

## Export Semantics

- JSON export should return `{ ok: true, filters, records }`.
- CSV export should include a header row and newline-terminated records.
- CSV columns should be:
  - `id`
  - `createdAt`
  - `action`
  - `status`
  - `recipientId`
  - `recipientName`
  - `recipientEmail`
  - `messageId`
  - `error`
- Export responses must set:
  - correct content type;
  - `content-disposition` attachment filename;
  - no raw SMTP secret material.
- Unsupported formats should return `400`.

## Suggested Implementation

- Extend `service/storage/smtp-operation-history-store.js` with focused helpers for:
  - filter normalization;
  - record filtering;
  - JSON export payload assembly;
  - CSV serialization.
- Update `service/app.js` to:
  - parse filter query params on `GET /configuration`;
  - pass filtered records and active filter values into the configuration view;
  - expose the export route.
- Update `service/views/configuration.js` to:
  - render filter controls;
  - preserve active filter selections;
  - render export links/buttons that keep the active filter query.

## Verification

Required gates:

- store tests for SMTP operational history filtering and CSV serialization;
- configuration page test proving filter controls and selected filter values render;
- route test proving filtered configuration history only shows matching SMTP operations;
- route tests proving JSON and CSV exports honor filters and return safe headers/content;
- regression checks proving delivery history remains separate from SMTP operational history.
