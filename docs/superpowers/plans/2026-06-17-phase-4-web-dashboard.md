# Phase 4 Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4 Fastify Web dashboard, configuration workbench, manual preview, logs route, JSON storage, and validation described in `docs/superpowers/specs/2026-06-17-phase-4-web-dashboard-design.md`.

**Architecture:** Keep Phase 4 inside the existing Node/Fastify companion service. `service/app.js` owns HTTP wiring, while focused modules own configuration defaults, validation, storage, and HTML rendering. Persist Phase 4 state as JSON in `OPENPET_DATA_DIR`; keep the current `.openpet-plugin.zip` command-only until the unified package phase.

**Tech Stack:** Node.js CommonJS, Fastify 5, built-in `node:test`, built-in `node:fs`, HTML string rendering with explicit escaping, existing `static/app.css`.

---

## File Structure

- Create `service/configuration/defaults.js`: default configuration and option constants.
- Create `service/configuration/validation.js`: form validation and normalization.
- Create `service/storage/configuration-store.js`: JSON load/save and recent log reading.
- Create `service/views/layout.js`: shared HTML shell and escaping helpers.
- Create `service/views/dashboard.js`: dashboard home/status page.
- Create `service/views/configuration.js`: configuration workbench page.
- Create `service/views/manual-preview.js`: manual preview confirmation page.
- Create `service/views/logs.js`: recent logs page.
- Modify `service/app.js`: add routes and form parsing.
- Modify `package.json`: add new service modules to `npm run typecheck`.
- Modify `tests/service-app.test.js`: add route, validation, persistence, secret-redaction, and logs tests.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 4 completion after implementation and review.

## Task 1: Storage And Initial Pages

**Files:**
- Create: `service/configuration/defaults.js`
- Create: `service/storage/configuration-store.js`
- Create: `service/views/layout.js`
- Create: `service/views/configuration.js`
- Create: `service/views/logs.js`
- Modify: `service/app.js`
- Test: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests proving `/configuration` creates a JSON config and `/logs` handles a missing log file:

```js
test('configuration page creates and renders service-owned default configuration', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.headers['content-type'], /text\/html/)
    assert.match(response.body, /配置中心/)
    assert.match(response.body, /收件人工作台/)
    assert.doesNotMatch(response.body, /\{[%{]/)
    assert.equal(existsSync(path.join(dataDir, 'configuration.json')), true)
  })
})

test('logs page renders an empty state when the log file is missing', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({ method: 'GET', url: '/logs' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /暂无服务日志/)
  })
})
```

- [ ] **Step 2: Verify RED**

Run: `npm test -- tests/service-app.test.js`

Expected: FAIL because `/configuration` and `/logs` are not registered.

- [ ] **Step 3: Implement storage and basic rendering**

Implement:

- `createDefaultConfiguration()` with defaults, empty recipients/schedules, SMTP metadata, providers, branding, and notifications.
- `loadConfiguration(paths)` creates `configuration.json` when missing and merges missing top-level keys with defaults.
- `saveConfiguration(paths, configuration)` writes pretty JSON.
- `readRecentLogs(paths, limit)` returns recent non-empty log lines or `[]`.
- `escapeHtml()`, `checked()`, `selected()`, and `renderPage()`.
- basic `renderConfigurationPage()` with sections `新用户默认值`, `收件人工作台`, `发送计划`, `邮件服务`, `天气数据源`, `报告品牌`, `通知与数据保留`.
- basic `renderLogsPage()` with `暂无服务日志` empty state.
- `GET /configuration` and `GET /logs` in `service/app.js`.

- [ ] **Step 4: Verify GREEN**

Run: `npm test -- tests/service-app.test.js`

Expected: PASS for new storage/page tests and existing service tests.

## Task 2: Dashboard And Escaped Rendering

**Files:**
- Create: `service/views/dashboard.js`
- Modify: `service/views/configuration.js`
- Modify: `service/app.js`
- Test: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests proving dashboard navigation and escaped user values:

```js
test('dashboard links to configuration logs and active CSS', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({ method: 'GET', url: '/' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /href="\/configuration"/)
    assert.match(response.body, /href="\/logs"/)
    assert.match(response.body, /href="\/static\/app\.css"/)
  })
})

test('configuration page escapes user-controlled values', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=%3Cscript%3Ealert(1)%3C%2Fscript%3E&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const response = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.doesNotMatch(response.body, /<script>alert/)
    assert.match(response.body, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
  })
})
```

- [ ] **Step 2: Verify RED**

Run: `npm test -- tests/service-app.test.js`

Expected: FAIL because POST `/configuration/recipients` and escaped recipient rendering are missing.

- [ ] **Step 3: Implement dashboard and recipient rendering**

Implement `renderDashboardPage({ configuration })` with service status, manual preview form entry, configuration/log links, and run-history empty state. Update configuration view to render recipient records through `escapeHtml`. Add minimal form parser in `service/app.js`:

```js
app.addContentTypeParser('application/x-www-form-urlencoded', { parseAs: 'string' }, (_request, body, done) => {
  done(null, Object.fromEntries(new URLSearchParams(body)))
})
```

Add a temporary valid recipient save path or complete Task 3 validation in the same implementation pass.

- [ ] **Step 4: Verify GREEN**

Run: `npm test -- tests/service-app.test.js`

Expected: PASS for dashboard navigation and escaped rendering tests.

## Task 3: Configuration Validation And Persistence

**Files:**
- Create: `service/configuration/validation.js`
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`
- Test: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests for recipient persistence and schedule validation:

```js
test('recipient form rejects invalid email and preserves safe form values', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=not-an-email&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /邮箱格式无效/)
    assert.match(response.body, /value="Mango"/)
  })
})

test('recipient form accepts a valid recipient and persists it', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(response.headers.location, '/configuration')
    assert.equal(configuration.recipients.length, 1)
    assert.equal(configuration.recipients[0].email, 'mango@example.com')
  })
})

test('schedule form rejects unknown recipient ids', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({
      method: 'POST',
      url: '/configuration/schedules',
      payload: 'recipient_id=missing&local_send_time=08%3A30&report_type=morning&send_policy=always&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /收件人不存在/)
  })
})
```

- [ ] **Step 2: Verify RED**

Run: `npm test -- tests/service-app.test.js`

Expected: FAIL until validation and POST routes are complete.

- [ ] **Step 3: Implement validation and POST routes**

Implement validators for:

- defaults: required location name/query/timezone/language/time/report type/send policy.
- recipients: required name/email/location/timezone/language/template/enabled; email must have exactly one `@`.
- schedules: recipient id must exist, time must match `HH:MM`, report type and send policy must be known.
- SMTP: port 1-65535 and security in `starttls`, `ssl`, `plain`.
- branding: accent color must match `#RRGGBB`.
- notifications: retention and cooldown must be non-negative integers.

On validation failure, render `/configuration` with status 400 and safe errors. On success, save and redirect `303` to `/configuration`.

- [ ] **Step 4: Verify GREEN**

Run: `npm test -- tests/service-app.test.js`

Expected: PASS for recipient and schedule validation tests.

## Task 4: SMTP, Branding, Manual Preview, And Logs

**Files:**
- Create: `service/views/manual-preview.js`
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`
- Modify: `service/views/logs.js`
- Test: `tests/service-app.test.js`

- [ ] **Step 1: Write failing tests**

Add tests for secret redaction, branding validation, and manual preview:

```js
test('smtp form never echoes submitted password', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const page = await app.inject({ method: 'GET', url: '/configuration' })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.smtp.passwordSaved, true)
    assert.doesNotMatch(JSON.stringify(configuration), /super-secret/)
    assert.doesNotMatch(page.body, /super-secret/)
    assert.match(page.body, /已保存，留空保持不变/)
  })
})

test('branding form rejects invalid accent color', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    const response = await app.inject({
      method: 'POST',
      url: '/configuration/branding',
      payload: 'report_title=Weather&accent_color=blue&footer_text=Footer&greeting_visible=on&data_source_visible=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /强调色必须是 #RRGGBB 格式/)
  })
})

test('manual preview renders confirmation without sending email', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({ env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir } })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const response = await app.inject({
      method: 'POST',
      url: '/manual/preview',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /手动发送预览/)
    assert.match(response.body, /确认并加入发送队列/)
    assert.doesNotMatch(response.body, /Email sent|SMTP|已发送/)
  })
})
```

- [ ] **Step 2: Verify RED**

Run: `npm test -- tests/service-app.test.js`

Expected: FAIL until SMTP redaction, branding validation, and manual preview are implemented.

- [ ] **Step 3: Implement remaining routes**

Wire `/configuration/defaults`, `/configuration/smtp`, `/configuration/branding`, `/configuration/notifications`, and `/manual/preview`. Store only `passwordSaved: true` for a submitted SMTP password. Manual preview must find the recipient, render a subject and plain-text preview, and avoid enqueueing or sending Email in Phase 4.

- [ ] **Step 4: Verify GREEN**

Run: `npm test -- tests/service-app.test.js`

Expected: PASS for all service tests.

## Task 5: Typecheck And Development Record

**Files:**
- Modify: `package.json`
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [ ] **Step 1: Update typecheck coverage**

Add the new service modules to `npm run typecheck`: `service/configuration/defaults.js`, `service/configuration/validation.js`, `service/storage/configuration-store.js`, and all files in `service/views/`.

- [ ] **Step 2: Add Phase 4 development record**

Append `## 13.5 Phase 4 Development Record` after the Phase 3 record. Include active routes, JSON storage boundary, validation coverage, secret redaction, test coverage, review status, and unchanged command-plugin package boundary.

- [ ] **Step 3: Run local verification**

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

Expected: all commands pass; `npm run package:plugin` still packages only the command-plugin files under `openpet-plugin/`.

## Task 6: Production Review And GitHub Update

**Files:**
- Review all Phase 4 changed files.
- Commit and push to `codex/phase-4-web-dashboard`.

- [ ] **Step 1: Run production review context**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Expected: output lists Phase 4 service/view/storage/test/doc files and safe check commands.

- [ ] **Step 2: Apply confirmed review findings**

Fix confirmed correctness, robustness, security, architecture, and test findings. Pay special attention to HTML escaping, secret redaction, file persistence, validation, and package boundary.

- [ ] **Step 3: Re-run verification**

Run the command set from Task 5 Step 3.

- [ ] **Step 4: Commit and push**

Run:

```bash
git add docs package.json service tests
git commit -m "Implement Phase 4 web dashboard migration"
git push
```

Expected: PR #3 updates and GitHub Actions starts.

- [ ] **Step 5: Check PR status**

Run:

```bash
gh pr view 3 --json state,isDraft,headRefOid,mergeStateStatus,statusCheckRollup,url
```

Expected: checks eventually report `SUCCESS`; if not, inspect logs and fix the root cause before continuing.
