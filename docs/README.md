# Weather Morning Report Documentation Index

> **Current implementation source of truth:** Weather Morning Report is now a dual-artifact OpenPet JavaScript extension/plugin. The compatibility package and unified extension package must follow the latest sibling OpenPet docs first: `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`, `/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`, and `/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md`.
>
> **Project source of truth:** `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` is the top-level development guide. `docs/PLUGIN_CONTRACT.md` owns stable command-plugin behavior. `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` and `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` own unified extension entries, services, dashboards, lifecycle, and data ownership.

## Active Docs

Read these first for all new development:

| Document | Purpose |
| --- | --- |
| `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` | Top-level strategic overview, current architecture, active TODO, document routing, development order, validation baseline |
| `docs/PLUGIN_CONTRACT.md` | Stable compatibility command-plugin contract: manifest, permissions, commands, config, data, storage, provider, rendering, privacy, build artifact |
| `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` | Unified OpenPet extension ecosystem boundary: root manifest, shell entries, services, dashboards, lifecycle, data ownership |
| `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` | Weather Morning Report service/dashboard migration ledger for Web dashboard, Email service, scheduler, templates, and unified extension package |
| `docs/MIGRATION_NOTES.md` | Implementation ledger and development manual: removed Python scope, current structure, build/package/test/release workflow, risks, done definition |
| `docs/RELEASE.md` | Release checklist for local verification, OpenPet validation, submission artifacts, artifact policy, and remaining release TODO |
| `legacy-assets/README.md` | Recovery ledger for historical Web, Email, SMTP, scheduler, database, and template assets restored for migration |

## How To Use The Docs

- New development question: start with `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`, then follow its contract and validation routing.
- Compatibility command-plugin question: use `docs/PLUGIN_CONTRACT.md`.
- Unified extension manifest, service, dashboard, lifecycle, data ownership, or host-boundary question: use `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md`.
- Web/Email/service/template migration status question: use `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
- Historical Web/Email/template asset question: use `legacy-assets/README.md` and `legacy-assets/recovered/`.
- Implementation sequencing, deletion scope, tests, packaging, OpenPet submission, or follow-up roadmap question: use `docs/MIGRATION_NOTES.md`.
- Release preparation question: use `docs/RELEASE.md`.
- If current OpenPet command-plugin behavior changes, update `docs/PLUGIN_CONTRACT.md` first, then update migration notes and release docs.
- If the unified extension model changes, update `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` first, then update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.

## Current Project Shape

This repository is currently an OpenPet JavaScript plugin project with a unified OpenPet extension package that restores Web and Email service capabilities.

- Framework-neutral weather modules live in `core/`.
- Framework-neutral text rendering lives in `rendering/`.
- OpenPet command adapter modules live in `src/`.
- Unified extension command entries live in `commands/`.
- Fastify companion service lives in `service/`.
- Active companion dashboard CSS lives in `static/`.
- Installable plugin root lives in `openpet-plugin/`.
- Bundled OpenPet entry is `openpet-plugin/index.js`.
- Compatibility package is generated at `release/weather-morning-report.openpet-plugin.zip`.
- Unified extension package is generated at `release/weather-morning-report.openpet-extension.zip`.
- Old Python service, Docker, systemd, SMTP, database, and Web UI docs were removed from the compatibility package surface.
- The unified extension package restores Web/Email/template product capability through OpenPet extension entries instead of reviving the old stack as-is.

## Maintenance Rules

- Keep stable plugin behavior in `docs/PLUGIN_CONTRACT.md`.
- Keep unified extension behavior in `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md`.
- Keep implementation status, validation commands, and risks in `docs/MIGRATION_NOTES.md`.
- Keep README files short and user-facing.
- Do not introduce compatibility command-plugin permissions, hosts, commands, or storage shapes without updating the current contract first.
- Do not introduce new unified extension entries, manifest declarations, service lifecycle, dashboard, setup, cleanup, or data ownership changes without updating the extension boundary docs first.
