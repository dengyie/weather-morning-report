# Phase 9 OpenPet Runtime Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automated OpenPet runtime smoke evidence for the unified extension package.

**Architecture:** Keep the target shell entries, then add a compatibility `main` bundle so current OpenPet can execute command handlers. A smoke script packages the extension and drives sibling OpenPet's `PluginService` APIs for dashboard, service lifecycle, health, command execution, and logs.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, Fastify service, sibling OpenPet `createPluginService`, zip packaging scripts.

---

## Task 1: Runtime-Compatible Unified Package

**Files:**
- Modify: `extension/plugin.json`
- Modify: `scripts/package-extension.js`
- Modify: `scripts/check-extension-artifact.js`
- Modify: `tests/extension-package.test.js`

- [x] **Step 1: Write failing package test**

Assert the unified manifest declares top-level `main`, runtime permissions, and network allowlist, and that the zip includes `compat/openpet-main.js`.

- [x] **Step 2: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/extension-package.test.js
```

Expected: fail because `extension/plugin.json` has no `main`, no top-level runtime permissions, and the zip does not include `compat/openpet-main.js`.

- [x] **Step 3: Add runtime manifest fields and package compat main**

Set:

```json
"main": "compat/openpet-main.js",
"permissions": ["network", "pet:say", "storage"],
"network": { "allowlist": ["wttr.in", "wttr.is"] }
```

Update `scripts/package-extension.js` to create `compat/` in the staged package and copy `openpet-plugin/index.js` to `compat/openpet-main.js` after `build-plugin.js` runs.

- [x] **Step 4: Extend extension artifact lint**

Make `scripts/check-extension-artifact.js` require the manifest `main` path, validate it is package-relative, and require that file in the zip.

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/extension-package.test.js
npm run package:extension
npm run lint:extension
```

Expected: all pass.

## Task 2: OpenPet Runtime Smoke Harness

**Files:**
- Create: `scripts/openpet-runtime-smoke.js`
- Create: `tests/openpet-runtime-smoke.test.js`
- Modify: `package.json`
- Modify: `.github/workflows/tests.yml`
- Modify: `.github/workflows/release.yml`

- [x] **Step 1: Write failing smoke test**

Create `tests/openpet-runtime-smoke.test.js` that runs `node scripts/openpet-runtime-smoke.js --json` and asserts:

- `dashboard.openedUrl` is `http://127.0.0.1:8787/`;
- service status reaches `running`, health is `healthy`, and stop returns a stopped/stopping runtime;
- command `status` returns `{ ok: true }`;
- logs include `dashboard:main`, `service:weather-service`, and `status`.

- [x] **Step 2: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/openpet-runtime-smoke.test.js
```

Expected: fail because `scripts/openpet-runtime-smoke.js` does not exist.

- [x] **Step 3: Implement smoke script**

Implement the script to:

- run `npm run package:extension`;
- extract `release/weather-morning-report.openpet-extension.zip` into a temporary OpenPet-style plugin directory;
- run `npm install --omit=dev --ignore-scripts --package-lock=false` in that temporary plugin directory;
- require sibling OpenPet `src/main/services/plugin-service.js`;
- create an in-memory settings service with plugin state;
- instantiate `createPluginService` with `pluginDirs: [releaseDir]`, pet/fetch/openExternal stubs, and a short health timeout;
- enable `weather-morning-report`;
- call `openDashboard('weather-morning-report', 'main')`;
- call `startService('weather-morning-report', 'weather-service')`;
- poll `checkServiceHealth` until healthy or timeout;
- call `runCommand('weather-morning-report', 'status')`;
- call `stopService`;
- output JSON evidence and stop all services in `finally`.

- [x] **Step 4: Add npm script**

Add:

```json
"smoke:openpet-runtime": "node scripts/openpet-runtime-smoke.js"
```

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/openpet-runtime-smoke.test.js
npm run smoke:openpet-runtime -- --json
```

Expected: both pass and the JSON evidence contains dashboard, service, command, and log proof.

- [x] **Step 6: Pin CI OpenPet runtime ref**

Set both GitHub workflows' OpenPet checkout to:

```yaml
ref: codex/plugin-service-health-checks
```

Expected: CI has the same OpenPet runtime service APIs used by Phase 9 smoke.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Modify: `docs/superpowers/plans/2026-06-17-phase-9-openpet-runtime-smoke.md`

- [x] **Step 1: Add Phase 9 development record**

Append `## 13.10 Phase 9 Development Record` with the runtime smoke behavior, compatibility `main` rationale, verification commands, and remaining non-goals.

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

Commit on `codex/phase-9-openpet-runtime-smoke`, push, and create a draft PR against `codex/phase-8-openpet-alignment`.
