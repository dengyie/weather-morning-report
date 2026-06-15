const { normalizeWttrPayload } = require('./wttr-parser')

const PROVIDER_HOSTS = ['wttr.in', 'wttr.is']

const createWttrUrl = (host, locationQuery) => `https://${host}/${encodeURIComponent(locationQuery)}?format=j1`

const assertWttrShape = (payload, host) => {
  if (!Array.isArray(payload?.current_condition) || payload.current_condition.length === 0) {
    throw new Error(`${host} response missing current_condition`)
  }
  if (!Array.isArray(payload?.weather) || payload.weather.length === 0) {
    throw new Error(`${host} response missing weather`)
  }
}

const parseResponse = (response, host, options) => {
  if (!response?.ok) {
    throw new Error(`${host} returned status ${response?.status || 'unknown'}`)
  }
  const payload = JSON.parse(response.text || '{}')
  assertWttrShape(payload, host)
  return normalizeWttrPayload(payload, {
    locationName: options.locationName,
    locationQuery: options.locationQuery,
    sourceHost: host,
    fetchedAt: options.fetchedAt
  })
}

const fetchWeatherSnapshot = async (options) => {
  const failures = []

  for (const host of PROVIDER_HOSTS) {
    try {
      const response = await options.fetchImpl(createWttrUrl(host, options.locationQuery), {
        headers: { accept: 'application/json' }
      })
      return parseResponse(response, host, options)
    } catch (error) {
      failures.push(`${host}: ${error.message || 'failed'}`)
    }
  }

  throw new Error(`Weather providers unavailable: ${failures.join('; ')}`)
}

module.exports = { PROVIDER_HOSTS, createWttrUrl, fetchWeatherSnapshot }
