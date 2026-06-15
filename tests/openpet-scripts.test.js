const test = require('node:test')
const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')

test('package script reports the created plugin archive', () => {
  const result = spawnSync('npm', ['run', 'package:plugin'], {
    cwd: repoRoot,
    encoding: 'utf8'
  })

  assert.equal(result.status, 0)
  assert.match(`${result.stdout}\n${result.stderr}`, /weather-morning-report\.openpet-plugin\.zip/)
})
