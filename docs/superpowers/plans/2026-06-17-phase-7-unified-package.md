# Phase 7 Unified Extension Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-validated unified OpenPet extension package artifact while preserving the existing command-plugin artifact.

**Architecture:** Keep the old `openpet-plugin/` package and `npm run package:plugin` path intact for the current OpenPet validator. Add a new `extension/plugin.json` manifest, package-relative command entrypoints under `commands/`, and a recursive `scripts/package-extension.js` packager that stages active runtime code into `release/weather-morning-report.openpet-extension.zip`. Add a local validator because the final OpenPet unified validator is not available yet.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, built-in `node:fs`, `node:child_process`, zip/unzip CLI, Fastify companion service files already present.

---

## File Structure

- Create `extension/plugin.json`: source unified extension manifest.
- Create `commands/runner.js`: shared stdin/env JSON command helper.
- Create `commands/weather-command.js`: shared shell weather command implementation using active core/rendering modules and command cache.
- Create `commands/refresh.js`, `commands/announce.js`, `commands/last.js`, `commands/status.js`, `commands/clear-cache.js`: shell command shims for current weather command behavior.
- Create `commands/send-email-now.js`: service-backed send-now shim.
- Create `commands/setup.js`: setup metadata shim.
- Create `scripts/package-extension.js`: stage and zip unified extension artifact.
- Create `scripts/check-extension-artifact.js`: validate unified zip structure and manifest consistency.
- Create `tests/extension-package.test.js`: package and validator coverage.
- Create `tests/extension-commands.test.js`: stdin/env/JSON command coverage.
- Modify `package.json`: add `package:extension`, `lint:extension`, and typecheck coverage.
- Modify `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`: append Phase 7 development record after implementation/review.

## Task 1: Unified Manifest Contract

**Files:**
- Create: `extension/plugin.json`
- Create: `tests/extension-package.test.js`

- [ ] **Step 1: Write failing manifest tests**

Add `tests/extension-package.test.js` with tests that read `extension/plugin.json` and assert the manifest has package-relative command/service/dashboard entries:

```js
const test = require('node:test')
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const manifestPath = path.join(repoRoot, 'extension/plugin.json')

const loadManifest = () => JSON.parse(readFileSync(manifestPath, 'utf8'))

test('unified extension manifest declares commands service dashboard and data boundaries', () => {
  const manifest = loadManifest()

  assert.equal(manifest.id, 'weather-morning-report')
  assert.equal(manifest.config, 'config.schema.json')
  assert.deepEqual(manifest.manifest.network, ['wttr.in', 'wttr.is'])
  assert.deepEqual(manifest.entries.commands.map((entry) => entry.id), [
    'refresh',
    'announce',
    'last',
    'status',
    'clear-cache',
    'send-email-now',
    'setup'
  ])
  assert.equal(manifest.entries.services[0].command, 'node service/index.js')
  assert.equal(manifest.entries.services[0].health.url, 'http://127.0.0.1:8787/health')
  assert.equal(manifest.entries.dashboards[0].url, 'http://127.0.0.1:8787')
  assert.ok(manifest.manifest.dataLocations.includes('OPENPET_DATA_DIR'))
  assert.ok(manifest.manifest.selfManagedSecrets.includes('SMTP password'))
})
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/extension-package.test.js
```

Expected: fail because `extension/plugin.json` does not exist.

- [ ] **Step 3: Add manifest**

Create `extension/plugin.json`:

```json
{
  "id": "weather-morning-report",
  "name": "Weather Morning Report",
  "version": "1.0.0",
  "description": "Weather reports with pet announcements, Web dashboard, scheduled Email delivery, and template-based previews.",
  "entries": {
    "commands": [
      { "id": "refresh", "title": "Refresh weather report", "command": "node commands/refresh.js", "cwd": "." },
      { "id": "announce", "title": "Announce weather report", "command": "node commands/announce.js", "cwd": "." },
      { "id": "last", "title": "Read last weather report", "command": "node commands/last.js", "cwd": "." },
      { "id": "status", "title": "Show weather report status", "command": "node commands/status.js", "cwd": "." },
      { "id": "clear-cache", "title": "Clear weather cache", "command": "node commands/clear-cache.js", "cwd": "." },
      { "id": "send-email-now", "title": "Send Email now", "command": "node commands/send-email-now.js", "cwd": "." },
      { "id": "setup", "title": "Setup Weather Morning Report", "command": "node commands/setup.js", "cwd": "." }
    ],
    "services": [
      {
        "id": "weather-service",
        "name": "Weather Morning Report Service",
        "command": "node service/index.js",
        "cwd": ".",
        "health": { "type": "http", "url": "http://127.0.0.1:8787/health" }
      }
    ],
    "dashboards": [
      { "id": "main", "title": "Weather Dashboard", "url": "http://127.0.0.1:8787" }
    ]
  },
  "manifest": {
    "network": ["wttr.in", "wttr.is"],
    "dataLocations": ["OPENPET_DATA_DIR", "OPENPET_CACHE_DIR", "OPENPET_LOG_DIR"],
    "externalAccounts": ["SMTP provider"],
    "selfManagedSecrets": ["SMTP username", "SMTP password"],
    "schedules": ["Morning weather Email schedule managed by the service."],
    "notes": [
      "The service binds to loopback by default.",
      "SMTP credentials are managed by the service, not by the OpenPet command runner.",
      "This manifest targets the upcoming unified OpenPet extension model and is validated locally until the official validator is available."
    ]
  },
  "config": "config.schema.json",
  "assets": ["static/**", "service/views/**", "README.md"]
}
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/extension-package.test.js
```

Expected: manifest test passes.

## Task 2: Shell Command JSON Shims

**Files:**
- Create: `commands/runner.js`
- Create: `commands/refresh.js`
- Create: `commands/announce.js`
- Create: `commands/last.js`
- Create: `commands/status.js`
- Create: `commands/clear-cache.js`
- Create: `commands/send-email-now.js`
- Create: `commands/setup.js`
- Create: `tests/extension-commands.test.js`

- [ ] **Step 1: Write failing command tests**

Create `tests/extension-commands.test.js`:

```js
const test = require('node:test')
const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')

const runCommand = (file, { input = '', env = {} } = {}) => {
  const result = spawnSync(process.execPath, [path.join(repoRoot, 'commands', file)], {
    cwd: repoRoot,
    input,
    encoding: 'utf8',
    env: { ...process.env, ...env }
  })
  return {
    ...result,
    json: result.stdout ? JSON.parse(result.stdout) : null
  }
}

test('setup command emits JSON metadata without running dependency installation', () => {
  const result = runCommand('setup.js')

  assert.equal(result.status, 0)
  assert.equal(result.json.ok, true)
  assert.equal(result.json.command, 'setup')
  assert.equal(result.json.requiresInstall, false)
})

test('status command consumes stdin JSON and environment defaults', () => {
  const result = runCommand('status.js', {
    input: '{"locationName":"Hangzhou"}',
    env: { OPENPET_DATA_DIR: '/tmp/openpet-data' }
  })

  assert.equal(result.status, 0)
  assert.equal(result.json.ok, true)
  assert.equal(result.json.command, 'status')
  assert.equal(result.json.input.locationName, 'Hangzhou')
  assert.equal(result.json.env.dataDirConfigured, true)
})

test('command shim rejects invalid stdin JSON without leaking environment secrets', () => {
  const result = runCommand('refresh.js', {
    input: '{bad',
    env: { SMTP_PASSWORD: 'super-secret' }
  })

  assert.notEqual(result.status, 0)
  assert.match(result.stderr, /Invalid JSON/)
  assert.doesNotMatch(result.stderr, /super-secret/)
})

test('send-email-now reports service requirement when no service URL is configured', () => {
  const result = runCommand('send-email-now.js', {
    input: '{"recipientId":"recipient-1","reportType":"morning"}',
    env: { OPENPET_SERVICE_URL: '' }
  })

  assert.equal(result.status, 0)
  assert.equal(result.json.ok, false)
  assert.equal(result.json.status, 'service_unavailable')
})
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/extension-commands.test.js
```

Expected: fail because `commands/*.js` files do not exist.

- [ ] **Step 3: Add shared runner and command shims**

Implement `commands/runner.js` with `readInputJson()`, `redact()`, and `runJsonCommand(command, handler)`. It should read stdin synchronously from fd `0`, parse optional JSON, redact `SMTP_PASSWORD` and `password=<value>` in fatal messages, and emit one JSON object to stdout.

Each basic weather command should call the runner and return:

```js
{
  ok: true,
  command: '<command-id>',
  input,
  env: {
    dataDirConfigured: Boolean(process.env.OPENPET_DATA_DIR),
    cacheDirConfigured: Boolean(process.env.OPENPET_CACHE_DIR),
    logDirConfigured: Boolean(process.env.OPENPET_LOG_DIR)
  }
}
```

`send-email-now.js` should return `{ ok: false, command: 'send-email-now', status: 'service_unavailable', message: 'OPENPET_SERVICE_URL is required for service-backed Email delivery in Phase 7.' }` when `OPENPET_SERVICE_URL` is blank.

`setup.js` should return `{ ok: true, command: 'setup', requiresInstall: false, message: 'Package dependencies are installed by the extension host or development setup before runtime commands execute.' }`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/extension-commands.test.js
```

Expected: command tests pass.

## Task 3: Unified Extension Packager

**Files:**
- Create: `scripts/package-extension.js`
- Modify: `tests/extension-package.test.js`
- Modify: `package.json`

- [ ] **Step 1: Write failing package tests**

Extend `tests/extension-package.test.js` with:

```js
const { existsSync } = require('node:fs')
const { rm, mkdir } = require('node:fs/promises')
const { execFileSync } = require('node:child_process')

const releaseDir = path.join(repoRoot, 'release')
const extensionArchivePath = path.join(releaseDir, 'weather-morning-report.openpet-extension.zip')

test('package:extension creates a unified extension zip with active runtime files', async () => {
  await rm(releaseDir, { recursive: true, force: true })
  await mkdir(releaseDir, { recursive: true })

  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })

  assert.equal(existsSync(extensionArchivePath), true)
  const listing = execFileSync('unzip', ['-Z1', extensionArchivePath], { encoding: 'utf8' })
    .trim()
    .split('\n')
    .sort()

  assert.ok(listing.includes('plugin.json'))
  assert.ok(listing.includes('config.schema.json'))
  assert.ok(listing.includes('package.json'))
  assert.ok(listing.includes('README.md'))
  assert.ok(listing.includes('commands/status.js'))
  assert.ok(listing.includes('commands/send-email-now.js'))
  assert.ok(listing.includes('core/weather-provider.js'))
  assert.ok(listing.includes('rendering/email-renderer.js'))
  assert.ok(listing.includes('service/index.js'))
  assert.ok(listing.includes('service/app.js'))
  assert.ok(listing.includes('static/app.css'))
  assert.equal(listing.some((file) => file.startsWith('legacy-assets/')), false)
  assert.equal(listing.some((file) => file.startsWith('docs/')), false)
  assert.equal(listing.some((file) => file.startsWith('tests/')), false)
  assert.equal(listing.some((file) => file.startsWith('node_modules/')), false)
  assert.equal(listing.some((file) => file.endsWith('.env')), false)
})
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/extension-package.test.js
```

Expected: fail because `package:extension` is missing.

- [ ] **Step 3: Implement packager**

Add `scripts/package-extension.js` that:

- runs `scripts/build-plugin.js`;
- removes `release/weather-morning-report-extension/`;
- creates a staging directory;
- copies `extension/plugin.json` to `plugin.json`;
- copies `openpet-plugin/config.schema.json`, `openpet-plugin/README.md`, and a package metadata file;
- recursively copies `commands/`, `core/`, `rendering/`, `service/`, and `static/`;
- writes an extension-scoped `package.json` containing `name`, `version`, `type`, `private`, `main`, `scripts.service:start`, and production dependencies from root `package.json`;
- zips all staged files recursively into `release/weather-morning-report.openpet-extension.zip`;
- prints the archive path.

Update `package.json`:

```json
"package:extension": "node scripts/package-extension.js"
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/extension-package.test.js
```

Expected: package tests pass and old `package:plugin` tests remain unaffected when full tests run.

## Task 4: Local Extension Artifact Validator

**Files:**
- Create: `scripts/check-extension-artifact.js`
- Modify: `tests/extension-package.test.js`
- Modify: `package.json`

- [ ] **Step 1: Write failing validator tests**

Extend `tests/extension-package.test.js` with:

```js
test('lint:extension validates manifest paths and URL consistency', () => {
  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })
  const output = execFileSync('npm', ['run', 'lint:extension'], {
    cwd: repoRoot,
    encoding: 'utf8'
  })

  assert.match(output, /Unified extension artifact check passed/)
})
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- tests/extension-package.test.js
```

Expected: fail because `lint:extension` is missing.

- [ ] **Step 3: Implement validator**

Add `scripts/check-extension-artifact.js` that:

- ensures the extension zip exists;
- lists zip files with `unzip -Z1`;
- reads `plugin.json` from the zip with `unzip -p`;
- asserts command entry files exist and use relative paths;
- asserts service command file exists;
- asserts dashboard URL origin matches service health URL origin;
- asserts required active files exist;
- rejects `legacy-assets/`, `docs/`, `tests/`, `release/`, `node_modules/`, `.env`, and `.git/`;
- prints `Unified extension artifact check passed.`

Update `package.json`:

```json
"lint:extension": "node scripts/check-extension-artifact.js"
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- tests/extension-package.test.js
npm run lint:extension
```

Expected: extension package tests and validator pass.

## Task 5: Typecheck Coverage And Compatibility

**Files:**
- Modify: `package.json`
- Modify: `tests/package-plugin.test.js` only if Phase 7 accidentally changes old package behavior

- [ ] **Step 1: Write or preserve compatibility expectations**

Run:

```bash
npm test -- tests/package-plugin.test.js tests/openpet-validate-zip.test.js
```

Expected before implementation: current command-plugin package tests pass.

- [ ] **Step 2: Update typecheck script**

Add `node --check` entries for:

- `commands/runner.js`
- `commands/weather-command.js`
- every `commands/*.js` shim;
- `scripts/package-extension.js`;
- `scripts/check-extension-artifact.js`.

- [ ] **Step 3: Verify package compatibility and syntax**

Run:

```bash
npm test -- tests/package-plugin.test.js tests/openpet-validate-zip.test.js
npm run typecheck
```

Expected: old package tests and typecheck pass.

## Task 6: Phase 7 Development Record, Review, Verification, Commit, Push

**Files:**
- Modify: `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`
- Review all Phase 7 files.

- [ ] **Step 1: Add Phase 7 development record**

Append `## 13.8 Phase 7 Development Record` after Phase 6. Include:

- dual-package transition;
- unified manifest and entry list;
- command JSON contract;
- included/excluded package paths;
- local validator scope;
- unchanged OpenPet current validator compatibility;
- Phase 8 remaining alignment.

- [ ] **Step 2: Run production review**

Run:

```bash
python3 /Users/mango/.agents/skills/production-code-quality-review/scripts/collect-review-context.py --repo /Users/mango/project/codex/weather-morning-report
```

Inspect the Phase 7 diff with focus on package boundary, secret exclusion, command execution behavior, and compatibility with the existing OpenPet validator. Fix confirmed findings with tests first.

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
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit and push**

Run:

```bash
git add commands docs extension package.json scripts tests
git commit -m "Implement Phase 7 unified extension package"
git push -u origin codex/phase-7-unified-package
```

Expected: branch pushed and ready for a draft PR against `codex/phase-6-scheduler`.
