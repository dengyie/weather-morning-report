# Weather Morning Report Documentation Index

> **Current implementation source of truth:** the existing command-plugin package must follow the latest sibling OpenPet docs first: `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`, `/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`, and `/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md`.
>
> **Next architecture direction:** `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` and `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` define the proposed developer-first unified extension model that future OpenPet work should enable.

## Active Docs

Read these first for all new development:

| Document | Purpose |
| --- | --- |
| `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` | New developer-first OpenPet extension ecosystem boundary: unified `plugin.json`, shell entries, services, dashboards, lifecycle, data ownership |
| `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` | New Weather Morning Report migration design for Web dashboard, Email service, scheduler, templates, and unified OpenPet extension package |
| `legacy-assets/README.md` | Recovery ledger for historical Web, Email, SMTP, scheduler, database, and template assets restored for migration |
| `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` | Current command-plugin strategic overview, current status, document routing, development order, validation baseline |
| `docs/PLUGIN_CONTRACT.md` | Current command-plugin contract: manifest, permissions, commands, config, data, storage, provider, rendering, privacy, build artifact |
| `docs/MIGRATION_NOTES.md` | Current command-plugin migration ledger and development manual: removed Python scope, current structure, build/package/test/release workflow, risks, done definition |
| `docs/RELEASE.md` | Current command-plugin release checklist for local verification, OpenPet validation, submission artifacts, and artifact policy |

## How To Use The Docs

- Current command-plugin product question: start with `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`.
- New OpenPet ecosystem boundary question: use `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md`.
- Web/Email/service/template migration question: use `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.
- Historical Web/Email/template asset question: use `legacy-assets/README.md` and `legacy-assets/recovered/`.
- Current command-plugin manifest, command, config, storage, network, privacy, data-shape, or artifact question: use `docs/PLUGIN_CONTRACT.md`.
- Current command-plugin implementation sequencing, deletion scope, tests, packaging, OpenPet submission, or follow-up roadmap question: use `docs/MIGRATION_NOTES.md`.
- Release preparation question: use `docs/RELEASE.md`.
- If current OpenPet command-plugin behavior changes, update `docs/PLUGIN_CONTRACT.md` first, then update migration notes and release docs.
- If the proposed unified extension model changes, update `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` first, then update `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`.

## Current Project Shape

This repository is currently an OpenPet JavaScript plugin project, with a new design direction toward a unified OpenPet extension package that also restores Web and Email service capabilities.

- Source modules live in `src/`.
- Installable plugin root lives in `openpet-plugin/`.
- Bundled OpenPet entry is `openpet-plugin/index.js`.
- Release package is generated at `release/weather-morning-report.openpet-plugin.zip`.
- Old Python service, Docker, systemd, SMTP, database, and Web UI docs were removed from the current command-plugin product surface.
- The new extension migration design intentionally restores Web/Email/template product capability through the unified extension service model instead of reviving the old stack as-is.

## Maintenance Rules

- Keep stable plugin behavior in `docs/PLUGIN_CONTRACT.md`.
- Keep proposed unified extension behavior in `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md`.
- Keep implementation status, validation commands, and risks in `docs/MIGRATION_NOTES.md`.
- Keep README files short and user-facing.
- Do not introduce current command-plugin permissions, hosts, commands, or storage shapes without updating the current contract first.
- Do not introduce new unified extension entries, manifest declarations, service lifecycle, dashboard, setup, cleanup, or data ownership changes without updating the extension boundary docs first.
