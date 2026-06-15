const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const { readFile } = require('node:fs/promises')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const pluginEntry = path.join(repoRoot, 'openpet-plugin/index.js')

test('build creates a single OpenPet runner-safe index.js', async () => {
  execFileSync('npm', ['run', 'build'], { cwd: repoRoot, stdio: 'pipe' })

  const builtSource = await readFile(pluginEntry, 'utf8')
  assert.equal(builtSource.includes('require('), false)
  assert.equal(builtSource.includes('process'), false)
  assert.equal(builtSource.includes("module.exports = function activate"), true)

  delete require.cache[require.resolve(pluginEntry)]
  const activate = require(pluginEntry)
  assert.equal(typeof activate, 'function')
})
