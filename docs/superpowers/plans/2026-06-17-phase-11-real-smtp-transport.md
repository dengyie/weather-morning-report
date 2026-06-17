# Phase 11 Real SMTP Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate a real SMTP transport for service-backed Email delivery without persisting raw SMTP secrets.

**Architecture:** Keep Email orchestration in `service/email/send-now.js`; add a focused SMTP transport in `service/email/transports.js` that converts service SMTP configuration into nodemailer options. `createServiceApp` should use the real transport by default while tests can continue injecting fake transports.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`, nodemailer.

---

## Task 1: SMTP Transport Contract Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [x] **Step 1: Write failing SMTP option mapping tests**

Add tests that call `createSmtpEmailTransport({ env, createTransport })` with fake `createTransport` and assert:

- `starttls` maps to `secure: false` and `requireTLS: true`;
- `ssl` maps to `secure: true`;
- `plain` maps to `secure: false` and `ignoreTLS: true`;
- username/password auth is included only when a username exists;
- timeout values use `SMTP_TIMEOUT_MS`.

- [x] **Step 2: Write failing missing configuration tests**

Assert real transport fails without SMTP host, sender identity, or required `SMTP_PASSWORD` when `passwordSaved` is true.

- [x] **Step 3: Write failing service default transport test**

Assert `createServiceApp` can send through a real transport factory when no `emailTransport` test double is injected.

- [x] **Step 4: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because `createSmtpEmailTransport` and service default wiring do not exist.

## Task 2: Implement Real SMTP Transport

**Files:**
- Modify: `service/email/transports.js`
- Modify: `service/email/send-now.js`
- Modify: `service/app.js`
- Modify: `package.json`
- Modify: `package-lock.json`

- [x] **Step 1: Add nodemailer dependency**

Run:

```bash
npm install nodemailer
```

- [x] **Step 2: Implement SMTP transport**

Add `createSmtpEmailTransport({ env, createTransport })` that:

- validates SMTP host before sending;
- validates sender email from envelope/config;
- validates `SMTP_PASSWORD` when `smtp.passwordSaved` is true;
- creates nodemailer transport options from `message.smtp`;
- sends `{ from, to, subject, text, html }`;
- returns nodemailer delivery metadata.

- [x] **Step 3: Pass SMTP configuration to transports**

Update `sendEmailNow` so `transport.send()` receives `smtp: configuration.smtp` alongside the rendered message.

- [x] **Step 4: Wire service default**

Update `createServiceApp` so the default `emailTransport` is `createSmtpEmailTransport({ env })`.

- [x] **Step 5: Add typecheck coverage**

Ensure `npm run typecheck` checks all changed modules.

- [x] **Step 6: Verify GREEN**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: all pass.

## Task 3: Documentation, Review, Verification, Commit, Push

**Files:**
- Create: `docs/superpowers/specs/2026-06-17-phase-11-real-smtp-transport-design.md`
- Create: `docs/superpowers/plans/2026-06-17-phase-11-real-smtp-transport.md`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [x] **Step 1: Add Phase 11 development record**

Document real SMTP activation, security mode mapping, runtime password boundary, tests, review status, and remaining non-goals.

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

Commit on `codex/phase-11-real-smtp-transport`, push, and create a draft PR against `codex/phase-10-setup-cleanup-lifecycle`.
