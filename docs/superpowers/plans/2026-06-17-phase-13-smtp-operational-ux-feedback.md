# Phase 13 SMTP Operational UX Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn SMTP test connection and test Email into configuration-page feedback workflows without breaking the existing JSON contract for non-page callers.

**Architecture:** Add page-mode notices to the configuration view and let the two SMTP operational routes switch between redirect/render behavior for browser forms and JSON behavior for API-style callers. Keep sender validation, recipient validation, and redaction behavior aligned with Phase 12.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`.

---

## Task 1: Write Failing UX Feedback Tests

**Files:**
- Modify: `tests/service-app.test.js`

- [x] **Step 1: Write failing configuration-page success notice test**

Assert the configuration page can render a success notice payload without losing the existing SMTP controls.

- [x] **Step 2: Write failing page-mode SMTP connection tests**

Add tests for:

- `POST /configuration/smtp/test-connection` with page-mode payload redirects back to `/configuration` on success;
- page-mode connection failures return HTML with a redacted warning instead of JSON.

- [x] **Step 3: Write failing page-mode test Email tests**

Add tests for:

- `POST /email/test` with page-mode payload redirects back to `/configuration` on success;
- success notice names the recipient safely;
- page-mode send failures return HTML with a redacted warning instead of JSON.

- [x] **Step 4: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/service-app.test.js
```

Expected: fail because page-mode notices and redirect/render behavior do not exist yet.

## Task 2: Implement Page-Mode Operational Feedback

**Files:**
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`
- Modify: `static/app.css`

- [x] **Step 1: Add success notice rendering**

Support a success notice block on the configuration page while keeping existing warning/error rendering.

- [x] **Step 2: Add page-mode route branching**

Detect form submissions that opt into page-mode behavior for SMTP operational actions.

- [x] **Step 3: Implement page-mode connection feedback**

Redirect successful SMTP connection tests back to `/configuration` with a success marker and re-render failures as HTML warnings.

- [x] **Step 4: Implement page-mode test Email feedback**

Redirect successful test Emails back to `/configuration` with a recipient-aware success marker and re-render failures as HTML warnings.

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/service-app.test.js
```

Expected: all pass.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-13-smtp-operational-ux-feedback-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-13-smtp-operational-ux-feedback.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [x] **Step 1: Add Phase 13 development record**

Document page-mode success/failure feedback, JSON compatibility, tests, and remaining non-goals.

- [x] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

Review result:

- Reviewed Phase 13 relative to `origin/codex/phase-12-smtp-operational-tests`.
- No confirmed merge-blocking findings remained after verifying route-mode separation, redaction behavior, and test coverage.

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

Commit on `codex/phase-13-smtp-operational-ux`, push, and create a draft PR against `codex/phase-12-smtp-operational-tests`.
