const test = require('node:test')
const assert = require('node:assert/strict')
const { renderWeatherText } = require('../src/text-renderer')

const baseReport = {
  subject: '天气早报 · 上海',
  focus: '今天午后有降雨风险，通勤建议带伞。',
  umbrella: '建议带伞。',
  sunscreen: '午间紫外线偏强，注意防晒。',
  clothing: '短袖外加轻薄外套即可。',
  closing: '出门前再看一眼天空，宠物也会替你盯着。',
  periods: [
    { label: '通勤', summary: '有小雨概率，路面可能湿滑。' },
    { label: '午间', summary: '紫外线偏强，户外注意防晒。' },
    { label: '晚间', summary: '降雨转弱，体感闷热。' }
  ]
}

const baseSnapshot = {
  location: { name: 'Shanghai', query: 'Shanghai' },
  source: { host: 'wttr.in', url: 'https://wttr.in/Shanghai?format=j1' },
  fetchedAt: '2026-06-16T00:00:00.000Z',
  current: { description: 'Partly cloudy', temperatureC: 27, feelsLikeC: 29 },
  daily: { minimumTemperatureC: 24, maximumTemperatureC: 31 }
}

test('renders a short summary and detail text in Chinese', () => {
  const rendered = renderWeatherText({ ...baseSnapshot, location: { ...baseSnapshot.location, name: '上海' } }, baseReport, {
    language: 'zh-CN',
    reportType: 'morning',
    includeSource: false,
    cached: false
  })

  assert.equal(rendered.summary, '天气早报 · 上海 · 27°C/体感29°C · 建议带伞 · 注意防晒')
  assert.match(rendered.detail, /今日重点：今天午后有降雨风险，通勤建议带伞。/)
})

test('renders an English summary when requested', () => {
  const rendered = renderWeatherText(baseSnapshot, {
    ...baseReport,
    subject: '[Rain likely, carry an umbrella] Weather report',
    focus: 'Rain is likely during your main outing periods.',
    umbrella: 'Carry a lightweight umbrella',
    sunscreen: 'UV 8; use strong protection, seek shade, and reapply outdoors',
    clothing: 'Wear a breathable light top and lightweight bottoms',
    closing: 'It will be hot today; remember to drink water.',
    periods: [
      { label: 'Morning commute', summary: 'Light rain possible.' },
      { label: 'Midday', summary: 'Strong UV.' },
      { label: 'Evening commute', summary: 'Comfortable.' }
    ]
  }, {
    language: 'en',
    reportType: 'morning',
    includeSource: true,
    cached: true
  })

  assert.match(rendered.summary, /^Weather report · Shanghai/)
  assert.match(rendered.detail, /Focus: Rain is likely during your main outing periods\./)
})
