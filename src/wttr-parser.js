const clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum)

const toFiniteNumber = (value, fallback = null) => {
  if (value == null) return fallback
  if (typeof value === 'string' && value.trim() === '') return fallback
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const toClampedNumber = (value, minimum, maximum, fallback = null) => {
  const number = toFiniteNumber(value, fallback)
  return number == null ? null : clamp(number, minimum, maximum)
}

const toNonNegativeNumber = (value, fallback = 0) => {
  const number = toFiniteNumber(value, fallback)
  return number == null ? null : Math.max(0, number)
}

const readDescription = (value) => {
  const description = value?.weatherDesc?.[0]?.value || value?.weatherDesc?.[0] || value?.weatherCode
  const normalized = String(description || '').trim()
  return normalized || 'Unknown'
}

const normalizeHourly = (hourly = []) => Array.isArray(hourly)
  ? hourly.map((item) => ({
      forecastAtHour: toFiniteNumber(item.time, 0) || 0,
      condition: readDescription(item),
      description: readDescription(item),
      temperatureC: toFiniteNumber(item.tempC, null),
      feelsLikeC: toFiniteNumber(item.FeelsLikeC, null),
      precipitationProbabilityPercent: toClampedNumber(item.chanceofrain, 0, 100, 0),
      precipitationMm: toNonNegativeNumber(item.precipMM, 0),
      thunderProbabilityPercent: toClampedNumber(item.chanceofthunder, 0, 100, 0),
      humidityPercent: toClampedNumber(item.humidity, 0, 100, null),
      windSpeedKph: toNonNegativeNumber(item.windspeedKmph, 0),
      uvIndex: toClampedNumber(item.uvIndex, 0, 30, 0)
    }))
  : []

const normalizeWttrPayload = (payload, options) => {
  const current = payload?.current_condition?.[0] || {}
  const day = payload?.weather?.[0] || {}
  const query = String(options.locationQuery || '').trim() || 'Unknown'
  const name = String(options.locationName || '').trim() || query

  return {
    schemaVersion: 1,
    location: { name, query },
    source: {
      host: options.sourceHost,
      url: `https://${options.sourceHost}/${encodeURIComponent(query)}?format=j1`
    },
    fetchedAt: options.fetchedAt,
    current: {
      condition: readDescription(current),
      description: readDescription(current),
      temperatureC: toFiniteNumber(current.temp_C, null),
      feelsLikeC: toFiniteNumber(current.FeelsLikeC, null),
      humidityPercent: toClampedNumber(current.humidity, 0, 100, null),
      windSpeedKph: toNonNegativeNumber(current.windspeedKmph, 0),
      uvIndex: toClampedNumber(current.uvIndex, 0, 30, 0)
    },
    daily: {
      date: String(day.date || '').trim(),
      minimumTemperatureC: toFiniteNumber(day.mintempC, null),
      maximumTemperatureC: toFiniteNumber(day.maxtempC, null),
      uvIndex: toClampedNumber(day.uvIndex, 0, 30, 0)
    },
    hourly: normalizeHourly(day.hourly)
  }
}

module.exports = { normalizeWttrPayload }
