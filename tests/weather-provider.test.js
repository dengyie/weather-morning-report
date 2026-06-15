const test = require('node:test')
const assert = require('node:assert/strict')
const { fetchWeatherSnapshot } = require('../src/weather-provider')

const samplePayload = {
  current_condition: [{ weatherDesc: [{ value: 'Sunny' }], temp_C: '25', FeelsLikeC: '26' }],
  weather: [{ date: '2026-06-16', mintempC: '21', maxtempC: '30', hourly: [] }]
}

test('fetches wttr.in first and normalizes a successful response', async () => {
  const calls = []
  const snapshot = await fetchWeatherSnapshot({
    locationName: 'Shanghai',
    locationQuery: 'Shanghai',
    fetchedAt: '2026-06-16T00:00:00.000Z',
    fetchImpl: async (url, options) => {
      calls.push({ url, options })
      return { ok: true, status: 200, text: JSON.stringify(samplePayload) }
    }
  })

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, 'https://wttr.in/Shanghai?format=j1')
  assert.deepEqual(calls[0].options, { headers: { accept: 'application/json' } })
  assert.equal(snapshot.source.host, 'wttr.in')
  assert.equal(snapshot.current.description, 'Sunny')
})

test('falls back to wttr.is after wttr.in fails', async () => {
  const calls = []
  const snapshot = await fetchWeatherSnapshot({
    locationName: 'Shanghai',
    locationQuery: 'Shanghai',
    fetchedAt: '2026-06-16T00:00:00.000Z',
    fetchImpl: async (url) => {
      calls.push(url)
      if (url.includes('wttr.in')) return { ok: false, status: 503, text: '' }
      return { ok: true, status: 200, text: JSON.stringify(samplePayload) }
    }
  })

  assert.deepEqual(calls, [
    'https://wttr.in/Shanghai?format=j1',
    'https://wttr.is/Shanghai?format=j1'
  ])
  assert.equal(snapshot.source.host, 'wttr.is')
})

test('throws a short provider error when all hosts fail', async () => {
  await assert.rejects(
    fetchWeatherSnapshot({
      locationName: 'Shanghai',
      locationQuery: 'Shanghai',
      fetchedAt: '2026-06-16T00:00:00.000Z',
      fetchImpl: async () => ({ ok: false, status: 500, text: '' })
    }),
    /Weather providers unavailable/
  )
})

test('treats missing required wttr fields as provider failure', async () => {
  await assert.rejects(
    fetchWeatherSnapshot({
      locationName: 'Shanghai',
      locationQuery: 'Shanghai',
      fetchedAt: '2026-06-16T00:00:00.000Z',
      fetchImpl: async () => ({ ok: true, status: 200, text: JSON.stringify({ weather: [] }) })
    }),
    /Weather providers unavailable/
  )
})
