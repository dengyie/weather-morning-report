# Phase 5 Email Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add active Email rendering, fake SMTP delivery, send-now behavior, and bounded delivery history for the Fastify companion service.

**Architecture:** Keep Email rendering deterministic in `rendering/`, delivery orchestration in `service/email/`, and JSON history persistence in `service/storage/`. The service accepts an injected Email transport for tests and reads runtime-only SMTP secret material from env instead of persisting raw passwords.

**Tech Stack:** Node.js CommonJS, Fastify 5, built-in `node:test`, built-in `node:fs`, existing core weather/recommendation modules, HTML string rendering with explicit escaping.

---

## File Structure

- Create `rendering/email-template-options.js`: legacy template ids, labels, default, normalization helpers.
- Create `rendering/email-renderer.js`: subject/plain/html/action summary rendering.
- Create `service/storage/delivery-history-store.js`: bounded JSON delivery history load/append.
- Create `service/email/transports.js`: fake transport and default runtime transport boundary.
- Create `service/email/send-now.js`: recipient lookup, report creation, rendering, sending, and history append.
- Create `service/views/email-preview.js`: Email preview page.
- Modify `service/app.js`: inject Email transport/env and add `GET /email/preview`, `POST /email/send-now`.
- Modify `package.json`: include new modules in `npm run typecheck`.
- Modify `tests/service-app.test.js`: service route and send-now coverage.
- Create `tests/email-renderer.test.js`: renderer and template option coverage.
- Create `tests/email-send-now.test.js`: transport/history orchestration coverage.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 5 completion after implementation/review.

## Task 1: Email Template Metadata And Renderer

**Files:**
- Create: `rendering/email-template-options.js`
- Create: `rendering/email-renderer.js`
- Create: `tests/email-renderer.test.js`
- Modify: `package.json`

- [ ] **Step 1: Write failing tests**

Add tests that import `EMAIL_TEMPLATE_OPTIONS`, `normalizeEmailTemplate`, `emailTemplateLabel`, and `renderEmailReport`. The tests should assert all five legacy labels, fallback to template `1`, HTML escaping, English labels, and one rendered HTML payload per template id.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/email-renderer.test.js
```

Expected: fail because `rendering/email-template-options.js` and `rendering/email-renderer.js` do not exist.

- [ ] **Step 3: Implement renderer**

Implement:

- `EMAIL_TEMPLATE_OPTIONS`
- `DEFAULT_EMAIL_TEMPLATE`
- `EMAIL_TEMPLATES`
- `emailTemplateLabel(value)`
- `normalizeEmailTemplate(value)`
- `renderEmailReport({ snapshot, advice, recipient, branding, reportType, cached })`

The renderer must return:

```js
{
  subject,
  text,
  html,
  templateId,
  templateLabel,
  actionSummary: {
    umbrella,
    sunscreen,
    clothing,
    riskLevel
  }
}
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/email-renderer.test.js
```

Expected: pass.

## Task 2: Delivery History Storage

**Files:**
- Create: `service/storage/delivery-history-store.js`
- Create: `tests/email-send-now.test.js`

- [ ] **Step 1: Write failing tests**

Add tests for `loadDeliveryHistory(paths)` and `appendDeliveryHistory(paths, record, { limit })`. The tests should assert the file is created under `OPENPET_DATA_DIR`, records are newest-last, old records are trimmed when the limit is exceeded, and HTML bodies/password-like fields are not stored by the caller.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/email-send-now.test.js
```

Expected: fail because the storage module does not exist.

- [ ] **Step 3: Implement bounded history storage**

Implement JSON persistence to `delivery-history.json` with:

- missing file returns `[]`;
- append writes pretty JSON with a trailing newline;
- records are sliced to the last `limit` entries;
- exported `deliveryHistoryPath(paths)`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/email-send-now.test.js
```

Expected: storage tests pass.

## Task 3: Fake Transport And Send-Now Orchestration

**Files:**
- Create: `service/email/transports.js`
- Create: `service/email/send-now.js`
- Modify: `tests/email-send-now.test.js`

- [ ] **Step 1: Write failing tests**

Add tests that:

- call `sendEmailNow({ paths, recipientId, reportType, transport, now, fetchReport })`;
- verify fake transport receives one rendered message;
- verify a `sent` delivery history record is stored without HTML body or secret values;
- verify a throwing transport records `failed` with a redacted error.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/email-send-now.test.js
```

Expected: fail because `send-now.js` and transport helpers do not exist.

- [ ] **Step 3: Implement send-now**

Implement:

- `createFakeEmailTransport()`;
- `createUnavailableEmailTransport(reason)`;
- `sendEmailNow({ paths, recipientId, reportType, transport, now, fetchReport })`;
- delivery history ids as `delivery-<timestamp>-<sequence or random-safe suffix>`;
- failed records with `status: "failed"` and redacted error text;
- successful records with `status: "sent"` and `messageId`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/email-send-now.test.js
```

Expected: pass.

## Task 4: Service Routes And Preview

**Files:**
- Create: `service/views/email-preview.js`
- Modify: `service/app.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests that:

- create a recipient through `/configuration/recipients`;
- call `GET /email/preview?recipient_id=recipient-1&report_type=morning`;
- assert HTML preview is returned and transport is not called;
- call `POST /email/send-now` with an injected fake transport;
- assert status 200 and delivery history contains `sent`;
- call `POST /email/send-now` with a missing recipient and assert status 400.

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/service-app.test.js
```

Expected: fail because the routes are missing.

- [ ] **Step 3: Implement service routes**

Update `createServiceApp({ env, emailTransport, fetchEmailReport })`:

- default `emailTransport` to `createUnavailableEmailTransport('SMTP transport is not configured')`;
- use a deterministic fixture report for preview/send-now until Phase 6 scheduler uses live report jobs;
- `GET /email/preview` renders selected Email HTML and does not call transport;
- `POST /email/send-now` calls `sendEmailNow` and returns JSON result;
- all 400 responses are safe and do not expose secret values.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/service-app.test.js
```

Expected: pass.

## Task 5: Review, Verification, Docs, Commit, Push

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Modify: `package.json`
- Review all Phase 5 files.

- [ ] **Step 1: Update typecheck coverage**

Add new files to `npm run typecheck`.

- [ ] **Step 2: Add Phase 5 development record**

Append `## 13.6 Phase 5 Development Record` after Phase 4. Include renderer, fake transport, send-now route, delivery history, secret redaction, test coverage, review status, and unchanged command-plugin package boundary.

- [ ] **Step 3: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Inspect Phase 5 rendering, transport, storage, routes, tests, docs, and packaging boundary. Fix confirmed findings.

- [ ] **Step 4: Run full verification**

Run:

```bash
npm ci
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
git diff --check
```

Expected: all pass.

- [ ] **Step 5: Commit and push**

Run:

```bash
git add docs package.json rendering service tests
git commit -m "Implement Phase 5 email delivery"
git push -u origin codex/phase-5-email-delivery
```

Expected: branch pushed and ready for a draft PR against `codex/phase-4-web-dashboard`.
