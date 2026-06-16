const test = require('node:test')
const assert = require('node:assert/strict')
const { scheduleFor } = require('../core/period-schedule')

test('morning schedules distinguish workdays and rest days', () => {
  const workday = scheduleFor(new Date('2026-06-08'))
  const restDay = scheduleFor(new Date('2026-06-06'))

  assert.deepEqual(workday.map((period) => period.label), ['早通勤', '午间', '晚通勤'])
  assert.deepEqual(restDay.map((period) => period.label), ['上午', '下午', '晚上'])
})

test('morning schedule uses UTC day from wttr date strings consistently', () => {
  const saturdayUtc = scheduleFor(new Date('2026-06-06T00:00:00Z'))

  assert.deepEqual(saturdayUtc.map((period) => period.label), ['上午', '下午', '晚上'])
})

test('midday and evening schedules match the documented contract', () => {
  assert.deepEqual(scheduleFor(new Date('2026-06-08'), 'midday').map((period) => period.label), ['下午', '晚上'])
  assert.deepEqual(scheduleFor(new Date('2026-06-08'), 'evening').map((period) => period.label), ['今晚', '次日早晨'])
})
