# Phase 7 Unified Extension Package Design

> Status: proposed for `codex/phase-7-unified-package`.
> Scope: Phase 7 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: final OpenPet lifecycle API conformance, real background worker daemon startup, dashboard authentication, SMTP secret storage migration, and catalog signing.

## Goal

Phase 7 introduces a unified extension package artifact while preserving the current command-plugin artifact as a compatibility baseline.

The unified artifact should make the active command, service, dashboard, static asset, and package metadata boundaries explicit. It should be testable in this repository before the future OpenPet unified extension validator is available.

## Recommended Approach

Use a dual-package transition:

- keep `release/weather-morning-report.openpet-plugin.zip` generated from `openpet-plugin/` for the current OpenPet validator;
- add `release/weather-morning-report.openpet-extension.zip` generated from a staging directory with a root `plugin.json`;
- add repository-local validation tests for the unified package structure and exclusion rules.

This approach avoids breaking the existing OpenPet command-plugin contract while Phase 7 moves the repo toward the target unified model documented in the migration plan.

## Unified Package Shape

The staged package root should contain:

- `plugin.json`
- `config.schema.json`
- `package.json`
- `README.md`
- `commands/`
- `core/`
- `rendering/`
- `service/`
- `static/`

The staged package root must not contain:

- `legacy-assets/`
- `docs/`
- `tests/`
- `release/`
- `.git/`
- `node_modules/`
- local data/cache/log directories
- `.env` files
- raw SMTP secrets

## Manifest Shape

Create a root-level source manifest at `extension/plugin.json`. The package script copies it to the staged package root as `plugin.json`.

The first manifest should follow the target shape already documented in the migration plan:

- `id`: `weather-morning-report`
- `name`: `Weather Morning Report`
- `version`: package version
- `description`: unified weather reports, dashboard, scheduled Email delivery, and pet announcements
- `entries.commands`: shell command entries for `refresh`, `announce`, `last`, `status`, `clear-cache`, `send-email-now`, and `setup`
- `entries.services`: `weather-service`, command `node service/index.js`
- `entries.dashboards`: dashboard URL `http://127.0.0.1:8787`
- `manifest.network`: `wttr.in`, `wttr.is`
- `manifest.dataLocations`: `OPENPET_DATA_DIR`, `OPENPET_CACHE_DIR`, `OPENPET_LOG_DIR`
- `manifest.selfManagedSecrets`: SMTP username/password
- `config`: `config.schema.json`
- `assets`: `static/**`, `service/views/**`, `README.md`

Because the final OpenPet unified schema is not available yet, Phase 7 validation should be strict about this repository's intended shape but should not claim catalog-level compatibility.

## Shell Command Entries

Add command entry files under `commands/`:

- `commands/refresh.js`
- `commands/announce.js`
- `commands/last.js`
- `commands/status.js`
- `commands/clear-cache.js`
- `commands/send-email-now.js`
- `commands/setup.js`

Each command should:

- read optional JSON from stdin;
- merge stdin config with environment defaults where appropriate;
- write JSON to stdout;
- write fatal diagnostics to stderr without secrets;
- exit `0` on successful command execution;
- exit non-zero on invalid input or unsupported runtime failures.

In Phase 7, command entries may delegate to existing command adapter/core behavior where practical. `send-email-now` may call the companion service HTTP endpoint when `OPENPET_SERVICE_URL` is provided and otherwise return a clear unavailable JSON response. `setup` should not run `npm install`; it should report setup metadata because package dependency installation remains outside the runtime command path.

## Packaging Scripts

Keep `scripts/package-plugin.js` as the compatibility packager for `.openpet-plugin.zip`.

Add:

- `scripts/package-extension.js`: builds the command bundle, stages the unified package, validates required files, zips the staging directory recursively, and prints the artifact path.
- `scripts/check-extension-artifact.js`: validates `release/weather-morning-report.openpet-extension.zip` without depending on an external OpenPet validator.

Update `package.json` with:

- `package:extension`
- `lint:extension`
- typecheck coverage for new scripts and command entries.

Do not change `npm run package:plugin` semantics in Phase 7.

## Validation Requirements

Add tests that prove:

- `npm run package:plugin` still creates the current four-file `.openpet-plugin.zip`;
- `npm run package:extension` creates `.openpet-extension.zip`;
- the unified zip has a root `plugin.json`;
- command, service, dashboard, static, core, and rendering files are included;
- local-only paths are excluded;
- command entries are package-relative and point to files in the zip;
- service health URL and dashboard URL use the same loopback origin;
- command entries consume stdin/env and emit JSON;
- `npm run lint:extension` rejects missing required package sections.

## Development Record

After implementation and production review, append `## 13.8 Phase 7 Development Record` to `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.

The record should include:

- dual-package transition behavior;
- unified manifest location and entry list;
- included and excluded package paths;
- command JSON contract;
- validation commands;
- production review findings and fixes;
- remaining OpenPet alignment work for Phase 8.

## Review And Release Gates

Before Phase 7 is committed:

1. Run `npm ci`, `npm test`, `npm run build`, `npm run lint`, `npm run lint:extension`, `npm run typecheck`, `npm run package:plugin`, `npm run package:extension`, and `git diff --check`.
2. Use `production-code-quality-review` on the Phase 7 diff.
3. Fix confirmed findings.
4. Update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` with the Phase 7 development record.
5. Commit and push `codex/phase-7-unified-package`.
