# Phase 9 OpenPet Runtime Smoke Design

> Status: proposed and implemented on `codex/phase-9-openpet-runtime-smoke`.
> Scope: Phase 9 of `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
> Non-scope: changing OpenPet core, catalog signing, and full Electron UI automation.

## Goal

Phase 9 turns the remaining OpenPet runtime evidence gaps into an automated smoke pass that runs this extension through the sibling OpenPet runtime service.

## Current OpenPet Findings

The sibling OpenPet repository exposes runtime support for local plugin discovery, enable/disable state, service start/stop, service health checks, dashboard opening, command logs, and legacy `main` command execution. It displays `entries.commands`, `entries.services`, and `entries.dashboards`, but the current command runner still executes plugin `main` handlers rather than directly spawning `entries.commands` shell declarations.

## Design

- Keep `entries.commands` as the target unified extension command surface.
- Add a compatibility `main` file to the packaged unified extension by copying the existing bundled `openpet-plugin/index.js` into `compat/openpet-main.js`.
- Add top-level runtime permissions and network allowlist to `extension/plugin.json` so the compatibility `main` can use OpenPet's current SDK permission checks.
- Add a repository smoke script that packages the extension, extracts the zip into a temporary OpenPet-style plugin directory, installs production dependencies in that temporary package, loads it through sibling OpenPet's `createPluginService`, enables the plugin, opens the dashboard, starts/stops the service, checks `/health`, runs a command, and verifies plugin logs.
- Use the sibling OpenPet checkout from `OPENPET_REPO_ROOT` or `../OpenPet`. If that checkout cannot expose unified extension manifests, the smoke script should fail clearly instead of claiming runtime evidence.
- GitHub Actions should checkout `dengyie/OpenPet@codex/plugin-service-health-checks` until the same runtime service APIs land on OpenPet `main`.
- Record the smoke output as evidence in the Phase 9 development record.

## Runtime Evidence

The smoke pass must prove:

- dashboard `main` opens through OpenPet's `openDashboard` path and records `dashboard:main`;
- service `weather-service` starts with OpenPet process lifecycle, answers `GET /health`, stops, and records `service:weather-service` logs;
- command `status` runs through OpenPet `runCommand`, returns JSON-compatible data, and records `Command completed`.

## Verification

Required gates:

- `npm test -- tests/openpet-runtime-smoke.test.js`
- `npm run package:extension`
- `npm run lint:extension`
- `npm run smoke:openpet-runtime`
- full phase gate after production review.
