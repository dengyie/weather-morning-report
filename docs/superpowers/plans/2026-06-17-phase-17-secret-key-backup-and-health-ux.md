# Phase 17 Secret Key Backup And Health UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configuration-page visibility and acknowledgement controls for local SMTP secret-key backup and managed secret health.

**Architecture:** Extend `service/storage/secret-store.js` with read-only health inspection helpers that never expose raw key or password material. Route code passes one normalized `secretHealth` model into the configuration view, while backup confirmation remains ordinary configuration metadata under `notifications.secretKeyBackupConfirmed`.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`, Node `fs`, existing service configuration and view helpers.

---

## File Structure

- Modify `service/storage/secret-store.js`: add normalized secret-health inspection helpers.
- Modify `service/app.js`: load secret health for configuration rendering and add backup-confirmation routes.
- Modify `service/views/configuration.js`: render secret-health UX and backup-confirmation controls.
- Modify `tests/email-send-now.test.js`: add secret-health unit coverage.
- Modify `tests/service-app.test.js`: add configuration rendering and route coverage.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 17 completion after implementation and review.

### Task 1: Write Failing Secret Health Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Add secret-store import in `tests/email-send-now.test.js`**

Update the existing `require('../service/storage/secret-store')` destructuring to include the new helper:

```js
const {
  clearStoredSmtpPassword,
  inspectSecretHealth,
  loadStoredSmtpPassword,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretsPath
} = require('../service/storage/secret-store')
```

- [ ] **Step 2: Write failing unit tests for normalized health state**

Add these tests after the existing managed SMTP secret storage tests:

```js
test('secret health reports informational state when no managed secret exists', async () => {
  await withTempServiceDirs(async (paths) => {
    assert.deepEqual(inspectSecretHealth(paths, { backupConfirmed: false }), {
      status: 'not-configured',
      backupConfirmed: false,
      warning: '',
      masterKey: { present: false, valid: false },
      managedSmtpPassword: { present: false, healthy: false, updatedAt: '' }
    })
  })
})

test('secret health reports healthy managed secret and backup warning state', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password', { now: new Date('2026-06-17T08:00:00.000Z') })

    assert.deepEqual(inspectSecretHealth(paths, { backupConfirmed: false }), {
      status: 'backup-unconfirmed',
      backupConfirmed: false,
      warning: '本地密钥尚未确认备份',
      masterKey: { present: true, valid: true },
      managedSmtpPassword: {
        present: true,
        healthy: true,
        updatedAt: '2026-06-17T08:00:00.000Z'
      }
    })

    assert.equal(inspectSecretHealth(paths, { backupConfirmed: true }).status, 'healthy')
  })
})

test('secret health reports invalid local key without exposing secret material', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password')
    require('node:fs').writeFileSync(secretKeyPath(paths), 'not-valid-base64')

    const health = inspectSecretHealth(paths, { backupConfirmed: false })

    assert.equal(health.status, 'unhealthy')
    assert.equal(health.masterKey.present, true)
    assert.equal(health.masterKey.valid, false)
    assert.equal(health.managedSmtpPassword.present, true)
    assert.equal(health.managedSmtpPassword.healthy, false)
    assert.match(health.warning, /本地密钥缺失或无效/)
    assert.doesNotMatch(JSON.stringify(health), /super-secret-password|not-valid-base64/)
  })
})

test('secret health reports corrupt managed SMTP payload without throwing', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password')
    const secrets = JSON.parse(readFileSync(secretsPath(paths), 'utf8'))
    secrets.smtpPassword.ciphertext = 'not-valid-base64'
    require('node:fs').writeFileSync(secretsPath(paths), `${JSON.stringify(secrets, null, 2)}\n`)

    const health = inspectSecretHealth(paths, { backupConfirmed: false })

    assert.equal(health.status, 'unhealthy')
    assert.equal(health.masterKey.valid, true)
    assert.equal(health.managedSmtpPassword.present, true)
    assert.equal(health.managedSmtpPassword.healthy, false)
    assert.match(health.warning, /已保存的 SMTP 密码无法解密/)
    assert.doesNotMatch(JSON.stringify(health), /super-secret-password|not-valid-base64/)
  })
})
```

- [ ] **Step 3: Add secret-store imports in `tests/service-app.test.js`**

Update the existing import to include the helpers used by the route tests:

```js
const {
  inspectSecretHealth,
  loadStoredSmtpPassword,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretsPath
} = require('../service/storage/secret-store')
```

- [ ] **Step 4: Write failing service tests for backup UX**

Add these tests near the existing SMTP secret route tests:

```js
test('configuration page renders secret health backup warning without leaking secret material', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /密钥与备份状态/)
    assert.match(page.body, /本地密钥尚未确认备份/)
    assert.match(page.body, /action="\/configuration\/secrets\/confirm-backup"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('secret backup confirmation routes toggle notification metadata', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    const confirmed = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    let configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    assert.equal(confirmed.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, true)

    const revoked = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/revoke-backup-confirmation',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(revoked.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, false)
  })
})

test('configuration page renders healthy secret backup state after confirmation', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.match(page.body, /本地密钥已确认备份/)
    assert.match(page.body, /action="\/configuration\/secrets\/revoke-backup-confirmation"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('configuration page renders degraded secret health without failing', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const paths = { dataDir, cacheDir, logDir }
    saveStoredSmtpPassword(paths, 'super-secret-password')
    require('node:fs').writeFileSync(secretKeyPath(paths), 'not-valid-base64')
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /本地密钥缺失或无效/)
    assert.doesNotMatch(page.body, /super-secret-password|not-valid-base64/)
  })
})
```

- [ ] **Step 5: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because `inspectSecretHealth`, backup-confirmation routes, and secret-health rendering do not exist yet.

### Task 2: Implement Secret Health Inspection

**Files:**
- Modify: `service/storage/secret-store.js`

- [ ] **Step 1: Add safe key validation helper**

Add a helper near `loadOrCreateSecretKey`:

```js
const inspectSecretKey = (paths) => {
  const file = secretKeyPath(paths)
  if (!existsSync(file)) {
    return { present: false, valid: false }
  }
  try {
    const key = decodeBase64(readFileSync(file, 'utf8'), 'SMTP secret key is invalid')
    return { present: true, valid: key.length === SECRET_KEY_BYTES }
  } catch {
    return { present: true, valid: false }
  }
}
```

- [ ] **Step 2: Add safe secret metadata loader**

Add:

```js
const inspectSecretsFile = (paths) => {
  try {
    return loadSecrets(paths)
  } catch {
    return null
  }
}
```

- [ ] **Step 3: Add normalized health inspection**

Add:

```js
const inspectSecretHealth = (paths, { backupConfirmed = false } = {}) => {
  const masterKey = inspectSecretKey(paths)
  const secrets = inspectSecretsFile(paths)
  const secretRecord = secrets && typeof secrets.smtpPassword === 'object'
    ? secrets.smtpPassword
    : null

  if (!secretRecord) {
    return {
      status: 'not-configured',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '',
      masterKey,
      managedSmtpPassword: { present: false, healthy: false, updatedAt: '' }
    }
  }

  if (!masterKey.valid) {
    return {
      status: 'unhealthy',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '本地密钥缺失或无效',
      masterKey,
      managedSmtpPassword: {
        present: true,
        healthy: false,
        updatedAt: secretRecord.updatedAt || ''
      }
    }
  }

  try {
    const stored = loadStoredSmtpPassword(paths)
    if (!stored) throw new Error('missing managed SMTP password')
    const healthy = {
      present: true,
      healthy: true,
      updatedAt: stored.updatedAt || ''
    }
    return {
      status: backupConfirmed ? 'healthy' : 'backup-unconfirmed',
      backupConfirmed: Boolean(backupConfirmed),
      warning: backupConfirmed ? '' : '本地密钥尚未确认备份',
      masterKey,
      managedSmtpPassword: healthy
    }
  } catch {
    return {
      status: 'unhealthy',
      backupConfirmed: Boolean(backupConfirmed),
      warning: '已保存的 SMTP 密码无法解密',
      masterKey,
      managedSmtpPassword: {
        present: true,
        healthy: false,
        updatedAt: secretRecord.updatedAt || ''
      }
    }
  }
}
```

- [ ] **Step 4: Export the new helper**

Update `module.exports` to include:

```js
inspectSecretHealth
```

- [ ] **Step 5: Verify store tests**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js
```

Expected: secret-health tests pass; route/view tests may still fail.

### Task 3: Wire Backup Confirmation Routes And View Model

**Files:**
- Modify: `service/app.js`

- [ ] **Step 1: Import `inspectSecretHealth`**

Update the secret-store import:

```js
const {
  clearStoredSmtpPassword,
  hasStoredSmtpPassword,
  inspectSecretHealth,
  loadStoredSmtpPassword,
  saveStoredSmtpPassword
} = require('./storage/secret-store')
```

- [ ] **Step 2: Add configuration view model helper**

Add near `configurationForView`:

```js
const configurationViewModel = (configuration, { hasManagedPassword = false, secretHealth } = {}) => ({
  ...configurationForView(configuration, smtpStateForView(configuration, { hasManagedPassword })),
  secretHealth
})
```

- [ ] **Step 3: Pass secret health into `GET /configuration`**

In `app.get('/configuration')`, compute:

```js
const secretHealth = inspectSecretHealth(paths, {
  backupConfirmed: configuration.notifications.secretKeyBackupConfirmed
})
```

Then pass:

```js
configuration: configurationViewModel(configuration, {
  hasManagedPassword: managedPasswordPresent,
  secretHealth
})
```

- [ ] **Step 4: Add backup confirmation routes**

Add routes near `/configuration/notifications`:

```js
app.post('/configuration/secrets/confirm-backup', async (_request, reply) => {
  const configuration = loadConfiguration(paths)
  configuration.notifications = {
    ...configuration.notifications,
    secretKeyBackupConfirmed: true
  }
  saveConfiguration(paths, configuration)
  return reply.code(303).header('location', '/configuration').send()
})

app.post('/configuration/secrets/revoke-backup-confirmation', async (_request, reply) => {
  const configuration = loadConfiguration(paths)
  configuration.notifications = {
    ...configuration.notifications,
    secretKeyBackupConfirmed: false
  }
  saveConfiguration(paths, configuration)
  return reply.code(303).header('location', '/configuration').send()
})
```

- [ ] **Step 5: Preserve existing error rendering**

Any route that re-renders `renderConfigurationPage` after an error and uses `configurationForView(...)` should pass a `secretHealth` model too. At minimum update SMTP page-mode error paths so the configuration page continues to render the secret-health section:

```js
const secretHealth = inspectSecretHealth(paths, {
  backupConfirmed: configuration.notifications.secretKeyBackupConfirmed
})
```

Use `configurationViewModel(configuration, { hasManagedPassword: managedPasswordPresent, secretHealth })`.

### Task 4: Render Secret Health UX

**Files:**
- Modify: `service/views/configuration.js`

- [ ] **Step 1: Add status labels**

Add near the SMTP labels:

```js
const SECRET_HEALTH_LABELS = {
  'not-configured': '尚未配置受管 SMTP 密码',
  'backup-unconfirmed': '需要确认密钥备份',
  healthy: '本地密钥已确认备份',
  unhealthy: '密钥或受管密码状态异常'
}
```

- [ ] **Step 2: Add secret health renderer**

Add before `renderNotificationsForm`:

```js
const renderSecretHealth = (secretHealth = {}) => {
  const masterKey = secretHealth.masterKey || {}
  const managedPassword = secretHealth.managedSmtpPassword || {}
  const status = secretHealth.status || 'not-configured'
  return renderSection('密钥与备份状态', '本地受管 SMTP 密钥的可见状态与备份确认。', `<div class="record-card">
    <h3>${escapeHtml(SECRET_HEALTH_LABELS[status] || status)}</h3>
    ${secretHealth.warning ? `<p class="notice-inline">${escapeHtml(secretHealth.warning)}</p>` : ''}
    <p class="muted">本地密钥：${masterKey.present ? '存在' : '尚未生成'} · ${masterKey.valid ? '有效' : '未验证或无效'}</p>
    <p class="muted">受管 SMTP 密码：${managedPassword.present ? '已保存' : '未保存'} · ${managedPassword.healthy ? '可解密' : '未验证或不可用'}</p>
    ${managedPassword.updatedAt ? `<p class="muted">最近更新：${escapeHtml(managedPassword.updatedAt)}</p>` : ''}
    <div class="quick-actions">
      ${secretHealth.backupConfirmed
        ? `<form method="post" action="/configuration/secrets/revoke-backup-confirmation">
          <button type="submit">撤销备份确认</button>
        </form>`
        : `<form method="post" action="/configuration/secrets/confirm-backup">
          <button type="submit"${managedPassword.present ? '' : ' disabled'}>标记已备份密钥</button>
        </form>`}
    </div>
  </div>`)
}
```

- [ ] **Step 3: Render secret health before notifications**

In `renderConfigurationPage`, insert:

```js
${renderSecretHealth(configuration.secretHealth)}
```

before:

```js
${renderNotificationsForm(values.notifications || configuration.notifications)}
```

- [ ] **Step 4: Verify focused route/view tests**

Run:

```bash
node --test --test-concurrency=1 tests/service-app.test.js
```

Expected: new route/view tests pass.

### Task 5: Documentation, Production Review, Verification, Publish

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`

- [ ] **Step 1: Add Phase 17 section to migration phase list**

After Phase 16 in the active phase list, add:

```md
### Phase 17: Secret Key Backup And Health UX

- Surface local master-key and managed SMTP secret health in the configuration workbench.
- Add explicit backup confirmation and revoke-confirmation actions.
- Keep raw key and password material out of HTML, JSON responses, logs, and history.

Done when:

- configuration page shows key presence, managed SMTP secret presence, and health state;
- operators can mark backup confirmation and revoke it;
- unhealthy key or managed secret state renders as a safe warning instead of breaking the page;
- no raw secret material is exposed by the new UX.
```

- [ ] **Step 2: Add Phase 17 development record**

After `## 13.23 Phase 16 Development Record`, add:

```md
## 13.24 Phase 17 Development Record

Phase 17 adds configuration-page visibility for local master-key backup acknowledgement and managed SMTP secret health.

Implemented artifacts:

- `docs/superpowers/specs/2026-06-17-phase-17-secret-key-backup-and-health-ux-design.md`
- `docs/superpowers/plans/2026-06-17-phase-17-secret-key-backup-and-health-ux.md`
- updated `service/storage/secret-store.js`
- updated `service/app.js`
- updated `service/views/configuration.js`
- expanded `tests/email-send-now.test.js`
- expanded `tests/service-app.test.js`

Operational behavior:

- configuration page displays local master-key presence and validity;
- configuration page displays managed SMTP password presence, decryptability, and last-updated metadata;
- operators can confirm or revoke local key backup acknowledgement;
- degraded key or managed-secret state is rendered as operator-safe warning copy without exposing secret material.

Validation coverage:

- secret-store tests cover healthy, not-configured, corrupt-key, and corrupt-payload health states;
- service route tests cover backup confirmation toggles;
- configuration page tests cover warning, healthy, and degraded render states without secret leakage.

Remaining SMTP work:

- raw key export/import and rotation remain out of scope;
- scheduler worker daemonization remains separate from secret backup UX.
```

- [ ] **Step 3: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Read the changed diff and fix confirmed findings with tests first.

- [ ] **Step 4: Run full verification**

Run:

```bash
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

- [ ] **Step 5: Commit, push, and create PR**

Commit on `codex/phase-17-secret-key-backup-and-health-ux`, push, and create a draft PR against `codex/phase-16-managed-smtp-secret-storage`.
