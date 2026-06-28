# Weather Morning Report

[English](README.md) | [简体中文](README.zh-CN.md)

Weather Morning Report is an **OpenPet JavaScript extension/plugin** for concise weather briefings.

It fetches public weather data from allowlisted providers, turns it into short action-oriented advice, and lets OpenPet announce reminders such as whether to bring an umbrella, use sunscreen, adjust clothing, or watch specific commute/midday/evening risks.

## Status

This repository now contains the plugin implementation, packaging workflow, and migration documentation.

- Plugin contract: `docs/PLUGIN_CONTRACT.md`
- Migration plan: `docs/MIGRATION_NOTES.md`
- Overview: `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`
- Docs index: `docs/README.md`

## Plugin Summary

- Plugin name: `Weather Morning Report`
- Plugin id: `com.weather-morning-report.openpet`
- Compatibility package: `.openpet-plugin.zip`
- Unified extension package: `.openpet-extension.zip`
- Permissions: `network`, `pet:say`, `storage`
- Network allowlist: `wttr.in`, `wttr.is`
- Commands: `refresh`, `announce`, `last`, `status`, `clear-cache`
- Extension entries: commands, setup, loopback service, and dashboard

## Development

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
```

OpenPet validation:

```bash
cd /Users/mango/project/codex/OpenPet
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-extension.zip
```

## Notes

- The compatibility plugin uses a single bundled `openpet-plugin/index.js` entry.
- The unified extension package declares `entries.commands`, `entries.setup`, `entries.services`, and `entries.dashboards` for current OpenPet main.
- The compatibility release archive contains only `plugin.json`, `config.schema.json`, `index.js`, and `README.md`.
- Legacy Python service code has been removed as part of the migration.
