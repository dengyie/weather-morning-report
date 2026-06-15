const test = require('node:test')
const assert = require('node:assert/strict')
const activate = require('../src/activate')

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

const cachedSnapshot = {
  schemaVersion: 1,
  location: { name: '上海', query: 'Shanghai' },
  source: { host: 'wttr.in', url: 'https://wttr.in/Shanghai?format=j1' },
  fetchedAt: new Date().toISOString(),
  current: { condition: 'Sunny', description: 'Sunny', temperatureC: 27, feelsLikeC: 29, humidityPercent: 60, windSpeedKph: 10, uvIndex: 2 },
  daily: { date: '2026-06-16', minimumTemperatureC: 24, maximumTemperatureC: 31, uvIndex: 8 },
  hourly: []
}

const createCtx = ({ config = {}, fetchImpl, storageSeed = {} } = {}) => {
  const speech = []
  const storage = new Map(Object.entries(storageSeed))
  return {
    speech,
    storage,
    ctx: {
      config: { get: (key) => key ? config[key] : config },
      network: { fetch: fetchImpl || (async () => ({ ok: true, status: 200, text: JSON.stringify(samplePayload) })) },
      pet: { say: async (message) => { speech.push(message) } },
      storage: {
        get: async (key, fallbackValue) => storage.has(key) ? storage.get(key) : fallbackValue,
        set: async (key, value) => { storage.set(key, value) },
        remove: async (key) => { storage.delete(key) },
        clear: async () => { storage.clear() }
      }
    }
  }
}

test('refresh fetches weather, stores normalized results, and announces when enabled', async () => {
  const harness = createCtx({ config: { locationName: '上海', locationQuery: 'Shanghai', announceOnRefresh: true } })
  const commands = activate(harness.ctx)

  const result = await commands.refresh()

  assert.equal(result.ok, true)
  assert.equal(result.cached, false)
  assert.equal(result.source, 'wttr.in')
  assert.match(result.summary, /天气早报 · 上海/)
  assert.equal(harness.speech.length, 1)
  assert.equal(harness.storage.get('last:summary'), result.summary)
  assert.equal(harness.storage.get('last:snapshot').source.host, 'wttr.in')
  assert.equal(harness.storage.get('stats').refreshCount, 1)
  assert.equal(harness.storage.get('stats').announceCount, 1)
})

test('announce speaks exactly once even when refresh announcements are enabled', async () => {
  const harness = createCtx({ config: { locationName: '上海', locationQuery: 'Shanghai', announceOnRefresh: true } })
  const commands = activate(harness.ctx)

  const result = await commands.announce()

  assert.equal(result.ok, true)
  assert.equal(harness.speech.length, 1)
  assert.equal(harness.speech[0], result.summary)
  assert.equal(harness.storage.get('stats').refreshCount, 1)
  assert.equal(harness.storage.get('stats').announceCount, 1)
})

test('provider failure uses fresh cached report', async () => {
  const harness = createCtx({
    config: { locationName: '上海', locationQuery: 'Shanghai', cacheMaxAgeMinutes: 120 },
    fetchImpl: async () => ({ ok: false, status: 503, text: '' }),
    storageSeed: {
      'last:snapshot': cachedSnapshot,
      'last:advice': { subject: 'cached' },
      'last:summary': 'cached summary',
      'last:detail': 'cached detail',
      stats: { refreshCount: 2, announceCount: 0, lastSuccessAt: cachedSnapshot.fetchedAt, lastFailureAt: null }
    }
  })
  const commands = activate(harness.ctx)

  const result = await commands.refresh()

  assert.equal(result.ok, true)
  assert.equal(result.cached, true)
  assert.equal(result.summary, 'cached summary')
  assert.match(result.warnings[0], /Weather providers unavailable/)
  assert.equal(harness.storage.get('last:error').providerHosts.length, 2)
  assert.equal(harness.storage.get('stats').lastFailureAt, harness.storage.get('last:error').at)
})

test('last announces the most recent cached summary', async () => {
  const harness = createCtx({ storageSeed: { 'last:snapshot': cachedSnapshot, 'last:summary': 'cached summary' } })
  const commands = activate(harness.ctx)

  const result = await commands.last()

  assert.equal(result.ok, true)
  assert.equal(harness.speech[0], 'cached summary')
})

test('status reports cache and config metadata without speaking', async () => {
  const harness = createCtx({ config: { locationName: '上海', locationQuery: 'Shanghai' }, storageSeed: { 'last:snapshot': cachedSnapshot, 'last:summary': 'cached summary' } })
  const commands = activate(harness.ctx)

  const result = await commands.status()

  assert.equal(result.ok, true)
  assert.equal(result.hasCache, true)
  assert.equal(result.config.locationName, '上海')
  assert.equal(harness.speech.length, 0)
})
