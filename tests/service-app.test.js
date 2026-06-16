const { existsSync, mkdtempSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const assert = require('node:assert/strict')

const { createServiceApp } = require('../service/app')

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const withTempServiceDirs = async (runner) => {
  const root = mkdtempSync(path.join(tmpdir(), 'wmr-service-'))
  try {
    await runner({
      dataDir: path.join(root, 'data'),
      cacheDir: path.join(root, 'cache'),
      logDir: path.join(root, 'logs')
    })
  } finally {
    rmSync(root, { force: true, recursive: true })
  }
}

test('Fastify service exposes a redacted health endpoint and prepares service directories', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'must-not-leak'
      }
    })

    const response = await app.inject({ method: 'GET', url: '/health' })
    await app.close()

    assert.equal(response.statusCode, 200)
    const body = response.json()
    assert.equal(body.ok, true)
    assert.equal(body.service, 'weather-morning-report')
    assert.equal(body.framework, 'fastify')
    assert.deepEqual(body.directories, { data: true, cache: true, logs: true })
    assert.equal(existsSync(dataDir), true)
    assert.equal(existsSync(cacheDir), true)
    assert.equal(existsSync(logDir), true)
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(dataDir)))
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(cacheDir)))
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(logDir)))
    assert.doesNotMatch(response.body, /must-not-leak/)
  })
})

test('Fastify service serves the dashboard shell and active CSS', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const dashboard = await app.inject({ method: 'GET', url: '/' })
    const css = await app.inject({ method: 'GET', url: '/static/app.css' })
    await app.close()

    assert.equal(dashboard.statusCode, 200)
    assert.match(dashboard.headers['content-type'], /text\/html/)
    assert.match(dashboard.body, /Weather Morning Report/)
    assert.match(dashboard.body, /href="\/static\/app\.css"/)

    assert.equal(css.statusCode, 200)
    assert.match(css.headers['content-type'], /text\/css/)
    assert.match(css.body, /:root/)
  })
})
