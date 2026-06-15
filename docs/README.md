# Weather Morning Report Documentation Index

> **Source of truth:** OpenPet plugin behavior must follow the latest sibling OpenPet docs first: `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`, `/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`, and `/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md`.

## Active Docs

Read these first for all new development:

| Document | Purpose |
| --- | --- |
| `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` | Strategic overview, current status, document routing, development order, validation baseline |
| `docs/PLUGIN_CONTRACT.md` | Stable OpenPet plugin contract: manifest, permissions, commands, config, data, storage, provider, rendering, privacy, build artifact |
| `docs/MIGRATION_NOTES.md` | Migration ledger and development manual: removed Python scope, current structure, build/package/test/release workflow, risks, done definition |
| `docs/RELEASE.md` | Release checklist for local verification, OpenPet validation, submission artifacts, and artifact policy |

## How To Use The Docs

- Product or architecture question: start with `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`.
- Manifest, command, config, storage, network, privacy, data-shape, or artifact question: use `docs/PLUGIN_CONTRACT.md`.
- Implementation sequencing, deletion scope, tests, packaging, OpenPet submission, or follow-up roadmap question: use `docs/MIGRATION_NOTES.md`.
- Release preparation question: use `docs/RELEASE.md`.
- If OpenPet has changed, update `docs/PLUGIN_CONTRACT.md` first, then update migration notes and release docs.

## Current Project Shape

This repository is now an OpenPet JavaScript plugin project.

- Source modules live in `src/`.
- Installable plugin root lives in `openpet-plugin/`.
- Bundled OpenPet entry is `openpet-plugin/index.js`.
- Release package is generated at `release/weather-morning-report.openpet-plugin.zip`.
- Old Python service, Docker, systemd, SMTP, database, and Web UI docs were removed from the active product surface.

## Maintenance Rules

- Keep stable plugin behavior in `docs/PLUGIN_CONTRACT.md`.
- Keep implementation status, validation commands, and risks in `docs/MIGRATION_NOTES.md`.
- Keep README files short and user-facing.
- Do not introduce permissions, hosts, commands, or storage shapes without updating the contract first.
