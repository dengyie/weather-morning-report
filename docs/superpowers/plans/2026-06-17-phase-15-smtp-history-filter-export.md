# Phase 15 SMTP Operational History Filter/Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add filtered SMTP operational history views and filtered JSON/CSV export from the configuration workbench without changing history retention boundaries or delivery history behavior.

**Architecture:** Keep SMTP operational history service-owned in `service/storage/`, add query-driven filtering in `service/app.js`, and render conservative filter/export controls inside the existing configuration page. Reuse the Phase 14 history store and keep exports limited to already-redacted persisted fields.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`.

---

## File Structure

- Modify `service/storage/smtp-operation-history-store.js`: add filter normalization, filtered reads, and CSV serialization.
- Modify `service/app.js`: parse filter query params and add export route.
- Modify `service/views/configuration.js`: render filter form and export links.
- Modify `tests/email-send-now.test.js`: add store-level filter/export tests.
- Modify `tests/service-app.test.js`: add configuration filter and export route tests.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 15 completion after implementation and review.

### Task 1: Write Failing Filter/Export Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Write failing store tests**

Add tests for:

- SMTP operational history filtering by action, status, and recipient id;
- CSV serialization with a header row and newline terminator.

- [ ] **Step 2: Write failing service tests**

Add tests for:

- filtered configuration page rendering with active filter controls;
- JSON export honoring filters;
- CSV export honoring filters and returning attachment headers;
- invalid export format returning `400`.

- [ ] **Step 3: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because filtering/export helpers and routes do not exist yet.

### Task 2: Implement SMTP History Filtering And Export

**Files:**
- Modify: `service/storage/smtp-operation-history-store.js`
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`

- [ ] **Step 1: Add store helpers**

Implement:

- `normalizeSmtpOperationHistoryFilters()`
- `filterSmtpOperationHistory()`
- `listSmtpOperationHistory()`
- `serializeSmtpOperationHistoryCsv()`

Keep invalid filters conservative by falling back to `all`.

- [ ] **Step 2: Wire filtered configuration history**

Update `GET /configuration` to:

- read filter query params;
- load filtered SMTP operational history;
- pass `smtpHistoryFilters` to the view.

- [ ] **Step 3: Add export route**

Add `GET /configuration/smtp/history/export` with:

- `format=json` returning `{ ok: true, filters, records }`;
- `format=csv` returning CSV text with download headers;
- `400` for unsupported formats.

- [ ] **Step 4: Render filter/export controls**

Render:

- action/status/recipient filters;
- submit button;
- JSON export link;
- CSV export link;
- active selections preserved in the UI.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: all pass.

### Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-15-smtp-history-filter-export-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-15-smtp-history-filter-export.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [ ] **Step 1: Add Phase 15 development record**

Document the new SMTP operational history filters, export route, tests, and remaining non-goals.

- [ ] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

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

Commit on `codex/phase-15-smtp-history-filter-export`, push, and create a draft PR against `codex/phase-14-smtp-operational-history`.
