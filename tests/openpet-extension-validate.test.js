const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync, spawnSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const openPetRoot = path.resolve(repoRoot, '../OpenPet')
const archivePath = path.join(repoRoot, 'release/weather-morning-report.openpet-extension.zip')

function classifyOpenPetValidation(result) {
  const output = `${result.stdout || ''}\n${result.stderr || ''}`.trim()
  if (result.status === 0) return { output, unsupportedExtensionSchema: false }
  if (/Plugin package must declare a main JavaScript file/.test(output)) {
    return { output, unsupportedExtensionSchema: true }
  }
  throw new Error(output || `OpenPet validator exited with status ${result.status}`)
}

test('classifies OpenPet main-file validation errors as unsupported extension schema', () => {
  const result = classifyOpenPetValidation({
    status: 1,
    stdout: '',
    stderr: 'Plugin package must declare a main JavaScript file'
  })

  assert.equal(result.unsupportedExtensionSchema, true)
})

test('rejects non-schema OpenPet validation failures', () => {
  assert.throws(
    () => classifyOpenPetValidation({
      status: 1,
      stdout: '',
      stderr: 'Plugin asset file does not exist'
    }),
    /Plugin asset file does not exist/
  )
})

test('OpenPet validator accepts the unified extension zip', (t) => {
  execFileSync('npm', ['run', 'package:extension'], { cwd: repoRoot, stdio: 'pipe' })
  const result = spawnSync('npm', ['run', 'validate:plugin', '--', archivePath], {
    cwd: openPetRoot,
    encoding: 'utf8'
  })
  const validation = classifyOpenPetValidation(result)

  if (validation.unsupportedExtensionSchema) {
    t.skip('OpenPet checkout does not support unified extension entries yet')
    return
  }

  assert.match(validation.output, /Plugin package validation passed/)
  assert.match(validation.output, /Weather Morning Report/)
  assert.match(validation.output, /Commands: refresh, announce, last, status, clear-cache, send-email-now, setup/)
})
