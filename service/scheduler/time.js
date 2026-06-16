const partsFor = (date, timezone) => {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone || 'UTC',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  })
  return Object.fromEntries(formatter.formatToParts(date).map((part) => [part.type, part.value]))
}

const localDateKey = (date, timezone) => {
  const parts = partsFor(date, timezone)
  return `${parts.year}-${parts.month}-${parts.day}`
}

const localTimeKey = (date, timezone) => {
  const parts = partsFor(date, timezone)
  return `${parts.hour}:${parts.minute}`
}

module.exports = { localDateKey, localTimeKey }
