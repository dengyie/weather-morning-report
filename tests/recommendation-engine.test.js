const test = require('node:test')
const assert = require('node:assert/strict')
const { recommendWeather } = require('../src/recommendation-engine')

const baseSnapshot = {
  schemaVersion: 1,
  location: { name: 'Shanghai', query: 'Shanghai' },
  source: { host: 'wttr.in', url: 'https://wttr.in/Shanghai?format=j1' },
  fetchedAt: '2026-06-16T00:00:00.000Z',
  current: {
    condition: 'Sunny',
    description: 'Sunny',
    temperatureC: 25,
    feelsLikeC: 26,
    humidityPercent: 60,
    windSpeedKph: 10,
    uvIndex: 2
  },
  daily: {
    date: '2026-06-16',
    minimumTemperatureC: 22,
    maximumTemperatureC: 30,
    uvIndex: 2
  },
  hourly: [
    { forecastAtHour: 900, condition: 'Cloudy', description: 'Cloudy', temperatureC: 25, feelsLikeC: 26, precipitationProbabilityPercent: 10, precipitationMm: 0, thunderProbabilityPercent: 0, humidityPercent: 60, windSpeedKph: 10, uvIndex: 2 },
    { forecastAtHour: 1200, condition: 'Cloudy', description: 'Cloudy', temperatureC: 27, feelsLikeC: 28, precipitationProbabilityPercent: 10, precipitationMm: 0, thunderProbabilityPercent: 0, humidityPercent: 60, windSpeedKph: 10, uvIndex: 8 },
    { forecastAtHour: 1800, condition: 'Cloudy', description: 'Cloudy', temperatureC: 26, feelsLikeC: 27, precipitationProbabilityPercent: 10, precipitationMm: 0, thunderProbabilityPercent: 0, humidityPercent: 60, windSpeedKph: 10, uvIndex: 1 }
  ]
}

test('prefers thunderstorm risk over heat and UV', () => {
  const snapshot = {
    ...baseSnapshot,
    hourly: baseSnapshot.hourly.map((point) => point.forecastAtHour === 1800
      ? { ...point, thunderProbabilityPercent: 60 }
      : point)
  }

  const advice = recommendWeather(snapshot, { reportType: 'morning', language: 'zh-CN' })

  assert.equal(advice.subject, '[雷雨风险，注意安全] 天气早报')
  assert.equal(advice.signals.thunderstorm, true)
  assert.equal(advice.umbrella, '建议带一把轻便伞')
})

test('uses workday commuting periods for morning reports', () => {
  const advice = recommendWeather(baseSnapshot, { reportType: 'morning', language: 'zh-CN' })

  assert.deepEqual(advice.periods.map((period) => period.label), ['早通勤', '午间', '晚通勤'])
  assert.deepEqual(advice.periods.map((period) => period.summary), [
    'Cloudy，降雨概率最高 10% ，体感约 26°C',
    'Cloudy，降雨概率最高 10% ，体感约 28°C',
    'Cloudy，降雨概率最高 10% ，体感约 27°C'
  ])
})

test('renders English summary and labels when requested', () => {
  const advice = recommendWeather(baseSnapshot, { reportType: 'morning', language: 'en' })

  assert.equal(advice.subject, '[Strong UV, use sun protection] Weather report')
  assert.equal(advice.umbrella, 'An umbrella is usually unnecessary today')
  assert.deepEqual(advice.periods.map((period) => period.label), [
    'Morning commute',
    'Midday',
    'Evening commute'
  ])
})

test('evening reports do not reuse same-day morning hours for next-morning risk', () => {
  const advice = recommendWeather({
    ...baseSnapshot,
    hourly: [
      { forecastAtHour: 700, condition: 'Thunderstorm', description: 'Thunderstorm', temperatureC: 25, feelsLikeC: 26, precipitationProbabilityPercent: 90, precipitationMm: 5, thunderProbabilityPercent: 80, humidityPercent: 80, windSpeedKph: 10, uvIndex: 0 },
      { forecastAtHour: 2000, condition: 'Clear', description: 'Clear', temperatureC: 25, feelsLikeC: 26, precipitationProbabilityPercent: 0, precipitationMm: 0, thunderProbabilityPercent: 0, humidityPercent: 60, windSpeedKph: 10, uvIndex: 0 }
    ]
  }, { reportType: 'evening', language: 'zh-CN' })

  assert.equal(advice.signals.thunderstorm, false)
  assert.deepEqual(advice.periods.map((period) => period.summary), [
    'Clear，降雨概率最高 0% ，体感约 26°C',
    '暂无可靠数据'
  ])
})
