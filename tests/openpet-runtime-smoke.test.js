const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')

test('OpenPet runtime smoke covers dashboard service command and logs', () => {
  const output = execFileSync(process.execPath, ['scripts/openpet-runtime-smoke.js', '--json'], {
    cwd: repoRoot,
    encoding: 'utf8'
  })
  const evidence = JSON.parse(output)

  assert.equal(evidence.pluginId, 'weather-morning-report')
  assert.equal(evidence.installed.fromArchive, true)
  assert.equal(evidence.installed.dependenciesInstalled, true)
  assert.equal(evidence.dashboard.openedUrl, 'http://127.0.0.1:8787/')
  assert.equal(evidence.service.start.runtime.status, 'running')
  assert.doesNotMatch(evidence.service.start.runtime.cwd, /weather-morning-report\/release/)
  assert.equal(evidence.service.health.health.status, 'healthy')
  assert.match(String(evidence.service.stop.runtime.status), /stopp|stopped/)
  assert.equal(evidence.command.status.ok, true)
  assert.equal(evidence.command.status.hasCache, false)

  const logKeys = evidence.logs.map((entry) => `${entry.commandId}:${entry.message}`)
  assert.ok(logKeys.some((line) => line.includes('dashboard:main:Dashboard opened')))
  assert.ok(logKeys.some((line) => line.includes('service:weather-service:Service started')))
  assert.ok(logKeys.some((line) => line.includes('service:weather-service:Service health healthy')))
  assert.ok(logKeys.some((line) => line.includes('status:Command completed')))
})
