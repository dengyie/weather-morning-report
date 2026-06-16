const compactAdvice = (value) => String(value || '')
  .replace(/^建议带一把轻便伞$/, '建议带伞')
  .replace(/^Carry a lightweight umbrella$/, 'Bring an umbrella')
  .replace(/。$/u, '')

const renderSummary = (snapshot, advice, options) => {
  const source = options.includeSource ? ` · ${snapshot.source.host}` : ''
  const locationName = snapshot.location.name
  if (options.language === 'en') {
    return `Weather report · ${locationName} · ${snapshot.current.temperatureC}°C, feels ${snapshot.current.feelsLikeC}°C · ${compactAdvice(advice.umbrella)} · ${compactAdvice(advice.sunscreen).split(';')[0]}${source}`
  }
  return `天气早报 · ${locationName} · ${snapshot.current.temperatureC}°C/体感${snapshot.current.feelsLikeC}°C · ${compactAdvice(advice.umbrella)} · ${compactAdvice(advice.sunscreen).includes('防晒') ? '注意防晒' : compactAdvice(advice.sunscreen)}${source}`
}

const renderDetail = (snapshot, advice, options) => {
  const periodLines = advice.periods.map((period) => `- ${period.label}：${period.summary}`).join('\n')
  if (options.language === 'en') {
    const cacheNotice = options.cached ? 'Note: live providers are unavailable; this report may use cached data.\n' : ''
    return `${cacheNotice}Focus: ${advice.focus}\nUmbrella: ${advice.umbrella}\nSun protection: ${advice.sunscreen}\nClothing: ${advice.clothing}\nCurrent: ${snapshot.current.description}, ${snapshot.current.temperatureC}°C, feels ${snapshot.current.feelsLikeC}°C\nKey periods:\n${periodLines}\n${advice.closing}`
  }
  const cacheNotice = options.cached ? '注意：实时天气源暂时不可用，以下建议可能基于缓存数据。\n' : ''
  return `${cacheNotice}今日重点：${advice.focus}\n带伞：${advice.umbrella}\n防晒：${advice.sunscreen}\n穿搭：${advice.clothing}\n当前：${snapshot.current.description}，${snapshot.current.temperatureC}°C，体感 ${snapshot.current.feelsLikeC}°C\n关键时段：\n${periodLines}\n${advice.closing}`
}

const renderWeatherText = (snapshot, advice, options = {}) => ({
  summary: renderSummary(snapshot, advice, options),
  detail: renderDetail(snapshot, advice, options)
})

module.exports = { renderWeatherText }
