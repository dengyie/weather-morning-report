# Phase 8 OpenPet Alignment Design

> Status: proposed and implemented on `codex/phase-8-openpet-alignment`.
> Scope: Phase 8 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: changing the OpenPet host, signing/catalog review, and full desktop UI smoke automation.

## Goal

Phase 8 aligns the unified extension package with the current sibling OpenPet validator and records the remaining runtime evidence gap honestly.

## Current OpenPet Findings

The sibling OpenPet repository now supports `entries.commands`, `entries.services`, `entries.dashboards`, service lifecycle declarations, service health declarations, and extension command entries. Its package validator accepts zip files with a root `plugin.json`, but it treats `assets` values as literal safe relative paths rather than glob patterns.

## Design

- Keep the dual-package transition from Phase 7.
- Update `extension/plugin.json` so `assets` names actual package paths: `static`, `service/views`, and `README.md`.
- Add a test that packages the unified extension and validates it with `../OpenPet`'s current `npm run validate:plugin`.
- Keep repository-local `lint:extension` because it checks package-specific exclusions and URL consistency that the generic OpenPet validator does not fully assert.
- Record that dashboard opening, service health UI state, and command log/result display require an OpenPet runtime smoke pass and remain evidence targets, not claims made by this repository-only phase.

## Verification

Required gates:

- `npm test -- tests/openpet-extension-validate.test.js`
- `npm run package:extension`
- `npm run lint:extension`
- full Phase 8 gate after production review.
