const test = require('node:test')
const assert = require('node:assert/strict')
const { normalizeWttrPayload } = require('../src/wttr-parser')

test('normalizes current, daily, and hourly wttr fields defensively', () => {
  const snapshot = normalizeWttrPayload({
    current_condition: [{
      weatherDesc: [{ value: 'Light rain' }],
      temp_C: '27',
      FeelsLikeC: '30',
      humidity: '81',
      windspeedKmph: '18',
      uvIndex: '7'
    }],
    weather: [{
      date: '2026-06-16',
      mintempC: '24',
      maxtempC: '31',
      uvIndex: '8',
      hourly: [{
        time: '900',
        weatherDesc: [{ value: 'Patchy rain nearby' }],
        tempC: '26',
        FeelsLikeC: '29',
        chanceofrain: '70',
        precipMM: '1.2',
        chanceofthunder: '45',
        humidity: '82',
        windspeedKmph: '21',
        uvIndex: '3'
      }]
    }]
  }, {
    locationName: 'Shanghai',
    locationQuery: 'Shanghai',
    sourceHost: 'wttr.in',
    fetchedAt: '2026-06-16T00:00:00.000Z'
  })

  assert.equal(snapshot.schemaVersion, 1)
  assert.deepEqual(snapshot.location, { name: 'Shanghai', query: 'Shanghai' })
  assert.equal(snapshot.source.host, 'wttr.in')
  assert.equal(snapshot.current.description, 'Light rain')
  assert.equal(snapshot.current.temperatureC, 27)
  assert.equal(snapshot.current.feelsLikeC, 30)
  assert.equal(snapshot.daily.maximumTemperatureC, 31)
  assert.equal(snapshot.hourly[0].forecastAtHour, 900)
  assert.equal(snapshot.hourly[0].precipitationProbabilityPercent, 70)
  assert.equal(snapshot.hourly[0].thunderProbabilityPercent, 45)
})

test('clamps unsafe numeric values and tolerates missing hourly data', () => {
  const snapshot = normalizeWttrPayload({
    current_condition: [{
      weatherDesc: [],
      temp_C: 'bad',
      FeelsLikeC: 'bad',
      humidity: '999',
      windspeedKmph: '-5',
      uvIndex: '999'
    }],
    weather: [{
      date: '2026-06-16',
      mintempC: 'bad',
      maxtempC: 'bad',
      uvIndex: '-3'
    }]
  }, {
    locationName: '',
    locationQuery: 'Shanghai',
    sourceHost: 'wttr.is',
    fetchedAt: '2026-06-16T00:00:00.000Z'
  })

  assert.deepEqual(snapshot.location, { name: 'Shanghai', query: 'Shanghai' })
  assert.equal(snapshot.current.description, 'Unknown')
  assert.equal(snapshot.current.temperatureC, null)
  assert.equal(snapshot.current.humidityPercent, 100)
  assert.equal(snapshot.current.windSpeedKph, 0)
  assert.equal(snapshot.current.uvIndex, 30)
  assert.equal(snapshot.daily.minimumTemperatureC, null)
  assert.equal(snapshot.daily.uvIndex, 0)
  assert.deepEqual(snapshot.hourly, [])
})
