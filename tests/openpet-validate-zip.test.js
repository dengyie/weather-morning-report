const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const openPetRoot = path.resolve(repoRoot, '../OpenPet')
const archivePath = path.join(repoRoot, 'release/weather-morning-report.openpet-plugin.zip')

test('OpenPet validator accepts the packaged plugin zip', () => {
  execFileSync('npm', ['run', 'build'], { cwd: repoRoot, stdio: 'pipe' })
  execFileSync('npm', ['run', 'package:plugin'], { cwd: repoRoot, stdio: 'pipe' })
  const output = execFileSync('npm', ['run', 'validate:plugin', '--', archivePath], {
    cwd: openPetRoot,
    encoding: 'utf8'
  })

  assert.match(output, /Plugin package validation passed/)
  assert.match(output, /com\.weather-morning-report\.openpet@1\.0\.0/)
})
