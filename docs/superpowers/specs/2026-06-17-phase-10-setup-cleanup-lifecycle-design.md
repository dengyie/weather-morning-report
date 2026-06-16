# Phase 10 Setup Cleanup Lifecycle Design

> Status: proposed and implemented on `codex/phase-10-setup-cleanup-lifecycle`.
> Scope: Phase 10 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: OpenPet core cleanup APIs, uninstall automation, dependency installation during package install, and third-party account cleanup.

## Goal

Phase 10 completes the repository-owned lifecycle surface for explicit setup and conservative cleanup.

The extension should declare setup in the OpenPet-supported `entries.setup` surface, keep setup available as a normal command for compatibility, and add a cleanup command that can be inspected or run explicitly by the user.

## Design

- Keep `commands/setup.js` metadata-only. It must not run `npm install` or mutate local files during package install.
- Add `commands/cleanup.js` as an explicit JSON command.
- Default cleanup to dry-run unless stdin includes `{ "confirm": true }`.
- Limit confirmed deletion to known Weather Morning Report service-owned files:
  - `OPENPET_DATA_DIR/configuration.json`
  - `OPENPET_DATA_DIR/delivery-history.json`
  - `OPENPET_DATA_DIR/scheduler-state.json`
  - `OPENPET_CACHE_DIR/weather-command-cache.json`, or `OPENPET_DATA_DIR/weather-command-cache.json` when no cache directory is provided
  - `OPENPET_LOG_DIR/service.log`
- Do not delete arbitrary directories, sibling files, external accounts, cloud data, SMTP provider data, or third-party-managed secrets.
- Add `cleanup` to `entries.commands` for current command execution surfaces.
- Add `setup` to `entries.setup` for OpenPet's setup lifecycle UI and runtime status.
- Add a compatibility `cleanup` handler to the bundled OpenPet `main` so current OpenPet runtimes that execute commands through `compat/openpet-main.js` do not expose a missing command.
- Keep compatibility cleanup conservative: dry-run by default and, when confirmed, clear only OpenPet command-plugin storage rather than service-owned files.
- Extend artifact validation so lifecycle setup entries use safe package-relative `node <file>` commands and included files.

## Verification

Required gates:

- cleanup command dry-run test
- cleanup confirmed deletion test
- unified manifest/package tests
- `npm run package:extension`
- `npm run lint:extension`
- full phase gate after production review
