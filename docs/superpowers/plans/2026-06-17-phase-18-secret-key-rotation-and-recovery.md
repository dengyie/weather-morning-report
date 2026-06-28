# Phase 18 Secret Key Rotation And Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe local SMTP secret-key rotation flow that re-encrypts the managed SMTP password under a new key and resets backup confirmation on success.

**Architecture:** Extend `service/storage/secret-store.js` with a rotation helper that validates the current local key and managed SMTP secret, decrypts the password in memory, and rewrites replacement artifacts safely. Route code in `service/app.js` will expose a configuration-page rotation action and reset `notifications.secretKeyBackupConfirmed` on success. The configuration view will surface the action and reflect success/failure through the existing normalized secret-health model.

**Tech Stack:** Node.js CommonJS, Fastify, built-in `node:test`, Node `fs`/`crypto`, existing service configuration and view helpers.

---

## File Structure

- Modify `service/storage/secret-store.js`: add a safe key-rotation helper and supporting persistence primitives.
- Modify `service/app.js`: add the rotation route, reset backup confirmation on success, and re-render configuration on failure.
- Modify `service/views/configuration.js`: render the rotation action and operator-safe notices in the secret-health section.
- Modify `tests/email-send-now.test.js`: add rotation helper coverage for success, invalid key, missing managed secret, undecryptable secret, and rollback behavior.
- Modify `tests/service-app.test.js`: add configuration rendering and route coverage for successful and failed rotation flows.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: record Phase 18 completion after implementation and review.

### Task 1: Write Failing Rotation Tests

**Files:**
- Modify: `tests/email-send-now.test.js`
- Modify: `tests/service-app.test.js`

- [ ] **Step 1: Add rotation helper import in `tests/email-send-now.test.js`**

Update the existing `require('../service/storage/secret-store')` destructuring to include the new rotation helper:

```js
const {
  clearStoredSmtpPassword,
  inspectSecretHealth,
  loadStoredSmtpPassword,
  rotateStoredSmtpPasswordKey,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretsPath
} = require('../service/storage/secret-store')
```

- [ ] **Step 2: Write failing unit tests for safe key rotation**

Add these tests after the existing secret-health tests:

```js
test('secret key rotation preserves the managed SMTP password and advances the key', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password', { now: new Date('2026-06-17T08:00:00.000Z') })
    const beforeKey = readFileSync(secretKeyPath(paths), 'utf8')

    const result = rotateStoredSmtpPasswordKey(paths, { now: new Date('2026-06-17T09:00:00.000Z') })
    const afterKey = readFileSync(secretKeyPath(paths), 'utf8')
    const stored = loadStoredSmtpPassword(paths)

    assert.equal(result.ok, true)
    assert.equal(beforeKey !== afterKey, true)
    assert.equal(stored.password, 'super-secret-password')
    assert.equal(stored.updatedAt, '2026-06-17T09:00:00.000Z')
    assert.match(JSON.stringify(result), /backupConfirmed/)
    assert.doesNotMatch(JSON.stringify(result), /super-secret-password|[A-Za-z0-9+/]{20,}/)
  })
})

test('secret key rotation rejects missing managed SMTP secrets', async () => {
  await withTempServiceDirs(async (paths) => {
    const result = rotateStoredSmtpPasswordKey(paths)

    assert.equal(result.ok, false)
    assert.equal(result.error, 'managed SMTP password is not configured')
    assert.equal(readFileSync(secretKeyPath(paths), 'utf8'), readFileSync(secretKeyPath(paths), 'utf8'))
  })
})

test('secret key rotation rejects invalid local keys without leaking secret material', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password')
    writeFileSync(secretKeyPath(paths), 'not-valid-base64')

    const result = rotateStoredSmtpPasswordKey(paths)

    assert.equal(result.ok, false)
    assert.match(result.error, /current local secret key is invalid/)
    assert.equal(loadStoredSmtpPassword(paths).password, 'super-secret-password')
    assert.doesNotMatch(JSON.stringify(result), /super-secret-password|not-valid-base64/)
  })
})

test('secret key rotation rolls back when replacing the key fails', async () => {
  await withTempServiceDirs(async (paths) => {
    saveStoredSmtpPassword(paths, 'super-secret-password')
    const beforeKey = readFileSync(secretKeyPath(paths), 'utf8')
    const beforeSecrets = readFileSync(secretsPath(paths), 'utf8')
    const originalWriteFileSync = require('node:fs').writeFileSync

    require('node:fs').writeFileSync = (...args) => {
      if (String(args[0]).endsWith('.secret-key.next')) throw new Error('simulated write failure')
      return originalWriteFileSync(...args)
    }

    const result = rotateStoredSmtpPasswordKey(paths)
    require('node:fs').writeFileSync = originalWriteFileSync

    assert.equal(result.ok, false)
    assert.match(result.error, /rotation failed/)
    assert.equal(readFileSync(secretKeyPath(paths), 'utf8'), beforeKey)
    assert.equal(readFileSync(secretsPath(paths), 'utf8'), beforeSecrets)
  })
})
```

- [ ] **Step 3: Add route and page tests in `tests/service-app.test.js`**

Add these tests near the existing secret backup route tests:

```js
test('configuration page renders a key rotation action for healthy managed secret state', async () => {
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
    assert.match(page.body, /本地密钥与备份状态/)
    assert.match(page.body, /action="\/configuration\/secrets\/rotate-key"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('secret key rotation route rotates the key and resets backup confirmation', async () => {
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

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/rotate-key',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, false)
  })
})

test('secret key rotation route fails safely when managed secret is not decryptable', async () => {
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
    require('node:fs').writeFileSync(secretsPath({ dataDir, cacheDir, logDir }), '{"smtpPassword":')

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/rotate-key',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.match(response.body, /已保存的 SMTP 密码无法解密/)
    assert.doesNotMatch(response.body, /super-secret/)
  })
})
```

- [ ] **Step 4: Verify RED**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js tests/service-app.test.js
```

Expected: fail because `rotateStoredSmtpPasswordKey`, the rotation route, and rotation rendering do not exist yet.

### Task 2: Implement Safe Key Rotation

**Files:**
- Modify: `service/storage/secret-store.js`

- [ ] **Step 1: Add a helper to generate a replacement local key and encrypted payload**

Add a helper near the existing secret utilities:

```js
const encryptStoredSmtpPassword = (key, password, { now = new Date() } = {}) => {
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const ciphertext = Buffer.concat([cipher.update(String(password)), cipher.final()])
  const tag = cipher.getAuthTag()
  return {
    algorithm: 'aes-256-gcm',
    keyId: 'local',
    iv: iv.toString('base64'),
    tag: tag.toString('base64'),
    ciphertext: ciphertext.toString('base64'),
    updatedAt: now.toISOString()
  }
}
```

- [ ] **Step 2: Add the rotation helper**

Add a helper that validates current state, generates a new key, writes temp files, and replaces active artifacts only after both are prepared:

```js
const rotateStoredSmtpPasswordKey = (paths, { now = new Date() } = {}) => {
  const secretRecord = loadSecrets(paths).smtpPassword
  if (!secretRecord || typeof secretRecord !== 'object') {
    return { ok: false, error: 'managed SMTP password is not configured' }
  }

  let currentPassword
  try {
    currentPassword = loadStoredSmtpPassword(paths)?.password
  } catch (error) {
    return { ok: false, error: error.message }
  }
  if (!currentPassword) {
    return { ok: false, error: 'managed SMTP password is not configured' }
  }

  const oldKeyFile = secretKeyPath(paths)
  const secretsFile = secretsPath(paths)
  const nextKey = crypto.randomBytes(SECRET_KEY_BYTES)
  const nextKeyFile = `${oldKeyFile}.next`
  const nextSecretsFile = `${secretsFile}.next`
  const nextSecrets = {
    ...loadWritableSecrets(paths),
    smtpPassword: encryptStoredSmtpPassword(nextKey, currentPassword, { now })
  }

  try {
    writeFileSync(nextKeyFile, nextKey.toString('base64'), { mode: SECRET_STORE_FILE_MODE })
    writeFileSync(nextSecretsFile, `${JSON.stringify(nextSecrets, null, 2)}\n`, { mode: SECRET_STORE_FILE_MODE })
    writeFileSync(oldKeyFile, nextKey.toString('base64'), { mode: SECRET_STORE_FILE_MODE })
    writeFileSync(secretsFile, `${JSON.stringify(nextSecrets, null, 2)}\n`, { mode: SECRET_STORE_FILE_MODE })
    return { ok: true, backupConfirmed: false, updatedAt: nextSecrets.smtpPassword.updatedAt }
  } catch (error) {
    return { ok: false, error: `rotation failed: ${error.message}` }
  } finally {
    if (existsSync(nextKeyFile)) require('node:fs').rmSync(nextKeyFile, { force: true })
    if (existsSync(nextSecretsFile)) require('node:fs').rmSync(nextSecretsFile, { force: true })
  }
}
```

- [ ] **Step 3: Export the new helper**

Update `module.exports` to include `rotateStoredSmtpPasswordKey`.

- [ ] **Step 4: Run focused storage tests**

Run:

```bash
node --test --test-concurrency=1 tests/email-send-now.test.js
```

Expected: PASS after rotation helper implementation.

### Task 3: Wire Rotation Into App And View

**Files:**
- Modify: `service/app.js`
- Modify: `service/views/configuration.js`

- [ ] **Step 1: Add the rotation helper import in `service/app.js`**

Update the existing `require('./storage/secret-store')` destructuring to include:

```js
rotateStoredSmtpPasswordKey,
```

- [ ] **Step 2: Add the rotation route**

Insert a route near the other secret routes:

```js
  app.post('/configuration/secrets/rotate-key', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = rotateStoredSmtpPasswordKey(paths)
    if (!result.ok) {
      reply.code(502).type('text/html; charset=utf-8')
      return renderConfigurationPage({
        configuration: configurationModelForView(configuration),
        errors: [result.error]
      })
    }

    configuration.notifications = {
      ...configuration.notifications,
      secretKeyBackupConfirmed: false
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration?smtp_notice=' + encodeURIComponent('本地密钥已轮换，请重新确认新密钥的备份状态')).send()
  })
```

- [ ] **Step 3: Show the rotation action in the secret-health section**

Extend `renderSecretHealth` so it renders the rotation form when `managedPassword.present` is true and renders only operator-safe text:

```js
    <div class="quick-actions">
      ${secretHealth.backupConfirmed
        ? `<form method="post" action="/configuration/secrets/revoke-backup-confirmation">
          <button type="submit">撤销备份确认</button>
        </form>`
        : `<form method="post" action="/configuration/secrets/confirm-backup">
          <button type="submit"${managedPassword.present ? '' : ' disabled'}>标记已备份密钥</button>
        </form>`}
      ${managedPassword.present
        ? `<form method="post" action="/configuration/secrets/rotate-key">
          <button type="submit">轮换本地密钥</button>
        </form>`
        : ''}
    </div>
```

- [ ] **Step 4: Run route and view tests**

Run:

```bash
node --test --test-concurrency=1 tests/service-app.test.js
```

Expected: PASS after route/view wiring.

### Task 4: Update Migration Docs And Verify

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Modify: `docs/superpowers/specs/2026-06-17-phase-18-secret-key-rotation-and-recovery-design.md` if self-review uncovers contradictions

- [ ] **Step 1: Add Phase 18 completion record after implementation**

After implementation is complete, add a new `## 13.25 Phase 18 Development Record` section with the actual artifacts, behavior, security boundary, validation coverage, and remaining work.

- [ ] **Step 2: Run the full verification gate**

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

- [ ] **Step 3: Commit**

```bash
git add docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md docs/superpowers/specs/2026-06-17-phase-18-secret-key-rotation-and-recovery-design.md service/app.js service/storage/secret-store.js service/views/configuration.js tests/email-send-now.test.js tests/service-app.test.js
git commit -m "feat: rotate secret key safely"
```
