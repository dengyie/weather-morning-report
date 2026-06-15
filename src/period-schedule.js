const WORKDAY_PERIODS = Object.freeze([
  { label: '早通勤', startHour: 700, endHour: 1000 },
  { label: '午间', startHour: 1100, endHour: 1400 },
  { label: '晚通勤', startHour: 1700, endHour: 2000 }
])

const REST_DAY_PERIODS = Object.freeze([
  { label: '上午', startHour: 800, endHour: 1100 },
  { label: '下午', startHour: 1200, endHour: 1700 },
  { label: '晚上', startHour: 1800, endHour: 2200 }
])

const MIDDAY_PERIODS = Object.freeze([
  { label: '下午', startHour: 1200, endHour: 1700 },
  { label: '晚上', startHour: 1700, endHour: 2200 }
])

const EVENING_PERIODS = Object.freeze([
  { label: '今晚', startHour: 1700, endHour: 2359 },
  { label: '次日早晨', startHour: 600, endHour: 1000, dayOffset: 1 }
])

const isWorkday = (date) => {
  const day = date.getUTCDay()
  return day >= 1 && day <= 5
}

const scheduleFor = (date, reportType = 'morning') => {
  if (reportType === 'midday') return [...MIDDAY_PERIODS]
  if (reportType === 'evening') return [...EVENING_PERIODS]
  if (reportType !== 'morning') throw new Error(`unsupported report type: ${reportType}`)
  return isWorkday(date) ? [...WORKDAY_PERIODS] : [...REST_DAY_PERIODS]
}

module.exports = { scheduleFor }
