# Phase 10 Setup Cleanup Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit setup lifecycle declaration and conservative cleanup command behavior for the unified OpenPet extension package.

**Architecture:** Keep lifecycle behavior in shell command entries owned by the extension. Use `entries.setup` for the OpenPet-supported setup surface, and expose cleanup as an explicit command with dry-run-by-default behavior until OpenPet adds a dedicated cleanup lifecycle API.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, local package validation scripts.

---

## Task 1: Lifecycle Manifest And Cleanup Tests

**Files:**
- Modify: `tests/extension-commands.test.js`
- Modify: `tests/extension-package.test.js`

- [x] **Step 1: Write failing cleanup command tests**

Assert `commands/cleanup.js`:

- dry-runs known service-owned files without deleting them;
- deletes only known service-owned files when stdin includes `{ "confirm": true }`;
- leaves unrelated files in data/cache/log directories untouched.
- removes command cache from the `OPENPET_DATA_DIR` fallback when no cache directory is configured.

- [x] **Step 2: Write failing manifest/package tests**

Assert:

- `entries.commands` includes `cleanup`;
- `entries.setup` declares `setup`;
- packaged extension includes `commands/cleanup.js`.

- [x] **Step 3: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/extension-commands.test.js
node --test --test-concurrency=1 tests/extension-package.test.js
```

Expected: fail because cleanup command and lifecycle manifest additions are missing.

## Task 2: Implement Conservative Lifecycle Surface

**Files:**
- Create: `commands/cleanup.js`
- Modify: `extension/plugin.json`
- Modify: `scripts/check-extension-artifact.js`
- Modify: `package.json`
- Modify: `src/commands.js`
- Modify: `openpet-plugin/index.js`

- [x] **Step 1: Add cleanup command**

Implement dry-run-by-default cleanup for:

- `configuration.json`
- `delivery-history.json`
- `scheduler-state.json`
- `weather-command-cache.json`
- `service.log`

Do not remove directories or unrelated files.

- [x] **Step 2: Add manifest lifecycle declarations**

Add `cleanup` to `entries.commands` and `setup` to `entries.setup`.

- [x] **Step 3: Extend package validation and typecheck**

Make `scripts/check-extension-artifact.js` validate setup lifecycle entry paths. Add `commands/cleanup.js` to `npm run typecheck`.

- [x] **Step 4: Add compatibility cleanup handler**

Add a conservative `cleanup` handler to the bundled OpenPet command adapter so current OpenPet runtimes executing through `compat/openpet-main.js` do not expose a missing command.

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/extension-commands.test.js
node --test --test-concurrency=1 tests/extension-package.test.js
node --test --test-concurrency=1 tests/openpet-phase1.test.js
```

Expected: all pass.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-10-setup-cleanup-lifecycle-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-10-setup-cleanup-lifecycle.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [x] **Step 1: Add Phase 10 development record**

Document explicit setup lifecycle, dry-run cleanup behavior, confirmed deletion boundary, validation coverage, and remaining non-goals.

- [x] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

- [x] **Step 3: Run full verification**

Run:

```bash
npm ci
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
npm run lint:extension
npm run smoke:openpet-runtime -- --json
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit, push, and create PR**

Commit on `codex/phase-10-setup-cleanup-lifecycle`, push, and create a draft PR against `codex/phase-9-openpet-runtime-smoke`.
