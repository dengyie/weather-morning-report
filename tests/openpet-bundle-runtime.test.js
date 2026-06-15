const test = require('node:test')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const bundlePath = path.join(repoRoot, 'openpet-plugin/index.js')

const samplePayload = {
  current_condition: [{ weatherDesc: [{ value: 'Sunny' }], temp_C: '27', FeelsLikeC: '29', humidity: '60', windspeedKmph: '10', uvIndex: '2' }],
  weather: [{
    date: '2026-06-16',
    mintempC: '24',
    maxtempC: '31',
    uvIndex: '8',
    hourly: []
  }]
}

test('the bundled OpenPet entry can activate and run commands', async () => {
  execFileSync('npm', ['run', 'build'], { cwd: repoRoot, stdio: 'pipe' })
  delete require.cache[require.resolve(bundlePath)]
  const activate = require(bundlePath)
  const speech = []
  const storage = new Map()
  const commands = activate({
    config: { get: () => ({ locationName: '上海', locationQuery: 'Shanghai' }) },
    network: {
      fetch: async () => ({ ok: true, status: 200, text: JSON.stringify(samplePayload) })
    },
    pet: { say: async (message) => { speech.push(message) } },
    storage: {
      get: async (key, fallbackValue) => storage.has(key) ? storage.get(key) : fallbackValue,
      set: async (key, value) => { storage.set(key, value) },
      clear: async () => { storage.clear() }
    }
  })

  const result = await commands.status()
  assert.equal(typeof activate, 'function')
  assert.equal(result.ok, true)
  assert.equal(result.config.locationName, '上海')
  assert.equal(speech.length, 0)
})
