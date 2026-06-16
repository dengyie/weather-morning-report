const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const openPetRoot = path.resolve(repoRoot, '../OpenPet')
const archivePath = path.join(repoRoot, 'release/weather-morning-report.openpet-extension.zip')

test('OpenPet validator accepts the unified extension zip', () => {
  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })
  const output = execFileSync('npm', ['run', 'validate:plugin', '--', archivePath], {
    cwd: openPetRoot,
    encoding: 'utf8'
  })

  assert.match(output, /Plugin package validation passed/)
  assert.match(output, /Weather Morning Report/)
  assert.match(output, /Commands: refresh, announce, last, status, clear-cache, send-email-now, setup/)
})
