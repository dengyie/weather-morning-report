# Phase 13 SMTP Operational UX Feedback Design

> Status: proposed on `codex/phase-13-smtp-operational-ux`.
> Scope: Phase 13 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: dashboard authentication, encrypted SMTP password storage, scheduler worker daemonization, provider OAuth, and OpenPet-owned secret management.

## Goal

Phase 13 makes SMTP operational actions feel native to the configuration workbench by returning users to the configuration page with explicit success or failure feedback instead of raw JSON.

## Design

- Extend the configuration page renderer to support success notices in addition to warning/error notices.
- Add a lightweight page-mode flag for SMTP operational forms so browser form submissions can request redirect-or-render behavior while preserving JSON responses for API-style callers.
- Update `POST /configuration/smtp/test-connection`:
  - in page mode, redirect to `/configuration` with a success notice after a successful verify;
  - in page mode, re-render `/configuration` with a redacted failure notice;
  - in non-page mode, keep the existing JSON response contract.
- Update `POST /email/test`:
  - in page mode, redirect to `/configuration` with a recipient-aware success notice after a successful send;
  - in page mode, re-render `/configuration` with a redacted failure notice;
  - in non-page mode, keep the existing JSON response contract.
- Keep recipient validation, sender validation, and SMTP secret redaction behavior unchanged.

## Verification

Required gates:

- configuration page rendering test for success notices;
- service route tests for page-mode SMTP connection success redirect and failure render;
- service route tests for page-mode test Email success redirect and failure render;
- regression checks proving JSON callers still receive JSON success/failure payloads;
- full phase gate after production review.
