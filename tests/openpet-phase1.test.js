const test = require('node:test')
const assert = require('node:assert/strict')
const { readFile } = require('node:fs/promises')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const readJson = async (relativePath) => JSON.parse(await readFile(path.join(repoRoot, relativePath), 'utf8'))

test('phase 1 OpenPet plugin skeleton matches the documented contract', async () => {
  const pkg = await readJson('package.json')
  const manifest = await readJson('openpet-plugin/plugin.json')
  const schema = await readJson('openpet-plugin/config.schema.json')
  const activate = require(path.join(repoRoot, 'openpet-plugin/index.js'))

  assert.equal(pkg.name, 'weather-morning-report')
  assert.match(pkg.scripts.test, /^node --test/)
  assert.match(pkg.scripts.test, /tests\/\*\*\/\*\.test\.js/)
  assert.equal(pkg.scripts.build, 'node scripts/build-plugin.js')
  assert.equal(pkg.scripts['package:plugin'], 'node scripts/package-plugin.js')

  assert.equal(manifest.id, 'com.weather-morning-report.openpet')
  assert.equal(manifest.main, 'index.js')
  assert.deepEqual(manifest.permissions, ['network', 'pet:say', 'storage'])
  assert.deepEqual(manifest.commands.map((command) => command.id), [
    'refresh',
    'announce',
    'last',
    'status',
    'clear-cache'
  ])

  assert.equal(schema.title, 'Weather Morning Report Settings')
  assert.equal(schema.type, 'object')
  assert.deepEqual(Object.keys(schema.properties), [
    'locationName',
    'locationQuery',
    'language',
    'reportType',
    'announceOnRefresh',
    'cacheMaxAgeMinutes',
    'includeSource'
  ])

  assert.equal(typeof activate, 'function')

  const commands = await activate({
    config: { get: () => ({}) },
    storage: {
      get: async () => null,
      set: async () => undefined,
      remove: async () => undefined,
      clear: async () => undefined
    },
    pet: {
      say: async () => undefined
    },
    network: {
      fetch: async () => { throw new Error('network should not be used in phase 1') }
    }
  })

  assert.equal(typeof commands.refresh, 'function')
  assert.equal(typeof commands.announce, 'function')
  assert.equal(typeof commands.last, 'function')
  assert.equal(typeof commands.status, 'function')
  assert.equal(typeof commands['clear-cache'], 'function')
})
