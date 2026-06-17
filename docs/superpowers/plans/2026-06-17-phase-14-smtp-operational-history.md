# Phase 14 SMTP Operational History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist bounded, redacted SMTP operational history and show recent operational checks in the configuration workbench without changing weather report delivery history behavior.

**Architecture:** Introduce a separate SMTP operational history store and wire both SMTP operational routes to append records on success/failure. Reuse existing service-owned JSON storage patterns and render the recent operational records inside the SMTP section of the configuration page.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`.

---

## Task 1: Write Failing History Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [x] **Step 1: Write failing SMTP operational history storage test**

Assert the new history store keeps bounded newest-last records and writes a newline-terminated JSON file.

- [x] **Step 2: Write failing route history tests**

Add tests for:

- SMTP test connection success appends an operational history record;
- SMTP test connection failure appends a redacted operational history record;
- test Email success appends an operational history record;
- test Email failure appends a redacted operational history record.

- [x] **Step 3: Write failing configuration history render test**

Assert the configuration page shows recent SMTP operational history entries while leaving existing controls intact.

- [x] **Step 4: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because the SMTP operational history store and rendering do not exist yet.

## Task 2: Implement SMTP Operational History

**Files:**
- Create: `service/storage/smtp-operation-history-store.js`
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`

- [x] **Step 1: Add bounded SMTP operational history store**

Implement load/save/append helpers using a service-owned JSON file and bounded newest-last semantics.

- [x] **Step 2: Record SMTP connection test history**

Append success and failure records for `POST /configuration/smtp/test-connection`.

- [x] **Step 3: Record test Email history**

Append success and failure records for `POST /email/test`.

- [x] **Step 4: Render recent SMTP operational history**

Show recent operational history entries in the configuration page near the SMTP controls.

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: all pass.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-14-smtp-operational-history-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-14-smtp-operational-history.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [x] **Step 1: Add Phase 14 development record**

Document the new SMTP operational history store, rendering, tests, and remaining non-goals.

- [x] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

Review result:

- Reviewed Phase 14 relative to `origin/codex/phase-13-smtp-operational-ux`.
- Confirmed one correctness gap: the early `收件人不存在` failure path in `/email/test` was not appending SMTP operational history even though the phase scope required success/failure coverage.
- Added a RED test for that path, fixed it, and re-ran focused tests to green.

- [ ] **Step 3: Run full verification**

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

Commit on `codex/phase-14-smtp-operational-history`, push, and create a draft PR against `codex/phase-13-smtp-operational-ux`.
