# Phase 12 SMTP Operational Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SMTP test connection and test Email operations to the service dashboard without persisting raw SMTP secrets.

**Architecture:** Extend the existing transport abstraction with `verify()` and add focused Fastify routes for operational checks. Keep send-now history separate: test Email sends a short operational message and does not write delivery history.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`, nodemailer.

---

## Task 1: SMTP Operation Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [x] **Step 1: Write failing SMTP verify test**

Assert `createSmtpEmailTransport({ createTransport })` exposes `verify(message)`, maps options like `send()`, calls the client's `verify()`, and returns `{ ok: true }`.

- [x] **Step 2: Write failing service route tests**

Add tests for:

- `POST /configuration/smtp/test-connection` succeeds through an injected transport `verify()`;
- test connection failures redact `SMTP_PASSWORD`;
- `POST /email/test` sends a short test Email to an existing recipient and does not write delivery history;
- configuration page renders controls for both operations.

- [x] **Step 3: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because `verify()`, the new routes, and page controls do not exist.

## Task 2: Implement SMTP Operational Routes

**Files:**
- Modify: `service/email/transports.js`
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`

- [x] **Step 1: Add transport verify**

Share SMTP option construction between `send()` and `verify()`. `verify()` should call the nodemailer client's `verify()` and return `{ ok: true }` when it resolves.

- [x] **Step 2: Add test connection route**

Implement `POST /configuration/smtp/test-connection` with success JSON and redacted 502 failures.

- [x] **Step 3: Add test Email route**

Implement `POST /email/test` with recipient validation, short text/html payload, SMTP configuration, no delivery history write, and redacted 502 failures.

- [x] **Step 4: Add configuration controls**

Render a test connection button and recipient-select test Email form in the SMTP section.

- [x] **Step 5: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: all pass.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-12-smtp-operational-tests-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-12-smtp-operational-tests.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [x] **Step 1: Add Phase 12 development record**

Document SMTP verify, test Email behavior, no-history boundary, redaction coverage, and remaining non-goals.

- [x] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Fix confirmed findings with tests first.

Review result:

- Found and fixed a route-level sender validation gap where injected transports could make SMTP test connection/test Email succeed without a configured sender.
- Added RED tests for both operational routes, verified the failure, then added `configuredSmtpSender()` to fail before transport side effects.

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

Result: all pass.

- [ ] **Step 4: Commit, push, and create PR**

Commit on `codex/phase-12-smtp-operational-tests`, push, and create a draft PR against `codex/phase-11-real-smtp-transport`.
