const test = require('node:test')
const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')

const samplePayload = {
  current_condition: [{
    weatherDesc: [{ value: 'Sunny' }],
    temp_C: '27',
    FeelsLikeC: '29',
    humidity: '60',
    windspeedKmph: '10',
    uvIndex: '2'
  }],
  weather: [{
    date: '2026-06-16',
    mintempC: '24',
    maxtempC: '31',
    uvIndex: '8',
    hourly: [
      { time: '900', weatherDesc: [{ value: 'Cloudy' }], tempC: '26', FeelsLikeC: '27', chanceofrain: '10', precipMM: '0', chanceofthunder: '0', humidity: '60', windspeedKmph: '10', uvIndex: '2' },
      { time: '1200', weatherDesc: [{ value: 'Cloudy' }], tempC: '27', FeelsLikeC: '29', chanceofrain: '10', precipMM: '0', chanceofthunder: '0', humidity: '60', windspeedKmph: '10', uvIndex: '8' },
      { time: '1800', weatherDesc: [{ value: 'Cloudy' }], tempC: '26', FeelsLikeC: '27', chanceofrain: '10', precipMM: '0', chanceofthunder: '0', humidity: '60', windspeedKmph: '10', uvIndex: '1' }
    ]
  }]
}

const withTempCache = (runner) => {
  const root = mkdtempSync(path.join(tmpdir(), 'wmr-extension-command-'))
  try {
    return runner(root)
  } finally {
    rmSync(root, { force: true, recursive: true })
  }
}

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

test('cleanup command dry-runs known service-owned files without deleting data', () => {
  withTempCache((root) => {
    const dataDir = path.join(root, 'data')
    const cacheDir = path.join(root, 'cache')
    const logDir = path.join(root, 'logs')
    mkdirSync(dataDir, { recursive: true })
    mkdirSync(cacheDir, { recursive: true })
    mkdirSync(logDir, { recursive: true })
    const files = [
      path.join(dataDir, 'configuration.json'),
      path.join(dataDir, 'delivery-history.json'),
      path.join(dataDir, 'scheduler-state.json'),
      path.join(dataDir, '.dashboard-token'),
      path.join(cacheDir, 'weather-command-cache.json'),
      path.join(logDir, 'service.log')
    ]
    for (const file of files) writeFileSync(file, '{}\n')

    const result = runCommand('cleanup.js', {
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    assert.equal(result.status, 0)
    assert.equal(result.json.ok, true)
    assert.equal(result.json.command, 'cleanup')
    assert.equal(result.json.dryRun, true)
    assert.deepEqual(result.json.deleted, [])
    assert.deepEqual(result.json.planned.map((entry) => entry.file).sort(), files.sort())
    for (const file of files) assert.equal(existsSync(file), true)
  })
})

test('cleanup command deletes only known service-owned files when confirmed', () => {
  withTempCache((root) => {
    const dataDir = path.join(root, 'data')
    const cacheDir = path.join(root, 'cache')
    const logDir = path.join(root, 'logs')
    mkdirSync(dataDir, { recursive: true })
    mkdirSync(cacheDir, { recursive: true })
    mkdirSync(logDir, { recursive: true })
    const serviceOwnedFiles = [
      path.join(dataDir, 'configuration.json'),
      path.join(dataDir, 'delivery-history.json'),
      path.join(dataDir, 'scheduler-state.json'),
      path.join(dataDir, '.dashboard-token'),
      path.join(cacheDir, 'weather-command-cache.json'),
      path.join(logDir, 'service.log')
    ]
    const unrelatedFiles = [
      path.join(dataDir, 'custom.json'),
      path.join(cacheDir, 'other-cache.json'),
      path.join(logDir, 'other.log')
    ]
    for (const file of serviceOwnedFiles.concat(unrelatedFiles)) writeFileSync(file, '{}\n')

    const result = runCommand('cleanup.js', {
      input: '{"confirm":true}',
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    assert.equal(result.status, 0)
    assert.equal(result.json.ok, true)
    assert.equal(result.json.dryRun, false)
    assert.deepEqual(result.json.deleted.map((entry) => entry.file).sort(), serviceOwnedFiles.sort())
    for (const file of serviceOwnedFiles) assert.equal(existsSync(file), false)
    for (const file of unrelatedFiles) assert.equal(existsSync(file), true)
  })
})

test('cleanup command removes command cache stored in OPENPET_DATA_DIR fallback', () => {
  withTempCache((dataDir) => {
    const cacheFile = path.join(dataDir, 'weather-command-cache.json')
    writeFileSync(cacheFile, '{}\n')

    const result = runCommand('cleanup.js', {
      input: '{"confirm":true}',
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: '' }
    })

    assert.equal(result.status, 0)
    assert.equal(result.json.ok, true)
    assert.equal(result.json.deleted.some((entry) => entry.file === cacheFile), true)
    assert.equal(existsSync(cacheFile), false)
  })
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

test('command JSON output redacts secret-looking input fields', () => {
  const result = runCommand('status.js', {
    input: '{"locationName":"Hangzhou","smtpPassword":"super-secret","nested":{"apiToken":"token-value"}}'
  })

  assert.equal(result.status, 0)
  assert.equal(result.json.input.locationName, 'Hangzhou')
  assert.equal(result.json.input.smtpPassword, '[redacted]')
  assert.equal(result.json.input.nested.apiToken, '[redacted]')
  assert.doesNotMatch(result.stdout, /super-secret|token-value/)
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

test('refresh renders a weather report and persists command cache', () => {
  withTempCache((cacheDir) => {
    const result = runCommand('refresh.js', {
      input: JSON.stringify({
        locationName: 'Shanghai',
        locationQuery: 'Shanghai',
        announceOnRefresh: false,
        weatherPayload: samplePayload
      }),
      env: { OPENPET_CACHE_DIR: cacheDir }
    })

    assert.equal(result.status, 0)
    assert.equal(result.json.ok, true)
    assert.equal(result.json.command, 'refresh')
    assert.equal(result.json.source, 'wttr.in')
    assert.match(result.json.summary, /天气早报 · Shanghai/)

    const status = runCommand('status.js', { env: { OPENPET_CACHE_DIR: cacheDir } })
    assert.equal(status.json.ok, true)
    assert.equal(status.json.hasCache, true)
    assert.equal(status.json.cachedAt, result.json.fetchedAt)
  })
})

test('last reads the persisted command cache and clear-cache removes it', () => {
  withTempCache((cacheDir) => {
    runCommand('refresh.js', {
      input: JSON.stringify({
        locationName: 'Shanghai',
        locationQuery: 'Shanghai',
        announceOnRefresh: false,
        weatherPayload: samplePayload
      }),
      env: { OPENPET_CACHE_DIR: cacheDir }
    })

    const last = runCommand('last.js', { env: { OPENPET_CACHE_DIR: cacheDir } })
    assert.equal(last.status, 0)
    assert.equal(last.json.ok, true)
    assert.equal(last.json.cached, true)
    assert.match(last.json.summary, /天气早报 · Shanghai/)

    const cleared = runCommand('clear-cache.js', { env: { OPENPET_CACHE_DIR: cacheDir } })
    assert.equal(cleared.json.cleared, true)
    const status = runCommand('status.js', { env: { OPENPET_CACHE_DIR: cacheDir } })
    assert.equal(status.json.hasCache, false)
  })
})
