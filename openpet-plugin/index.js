const DEFAULT_CONFIG = Object.freeze({
  locationName: 'Shanghai',
  locationQuery: 'Shanghai',
  language: 'zh-CN',
  reportType: 'morning',
  announceOnRefresh: true,
  cacheMaxAgeMinutes: 120,
  includeSource: false
})

const allowedLanguages = new Set(['zh-CN', 'en'])
const allowedReportTypes = new Set(['morning', 'midday', 'evening'])
const allowedCacheAges = new Set([30, 60, 120, 240])

const cleanString = (value) => String(value || '').trim()

const normalizeConfig = (rawConfig = {}) => {
  const locationName = cleanString(rawConfig.locationName) || cleanString(rawConfig.locationQuery) || DEFAULT_CONFIG.locationName
  const locationQuery = cleanString(rawConfig.locationQuery) || locationName
  const language = allowedLanguages.has(rawConfig.language) ? rawConfig.language : DEFAULT_CONFIG.language
  const reportType = allowedReportTypes.has(rawConfig.reportType) ? rawConfig.reportType : DEFAULT_CONFIG.reportType
  const cacheMaxAgeMinutes = allowedCacheAges.has(Number(rawConfig.cacheMaxAgeMinutes))
    ? Number(rawConfig.cacheMaxAgeMinutes)
    : DEFAULT_CONFIG.cacheMaxAgeMinutes

  return {
    locationName,
    locationQuery,
    language,
    reportType,
    announceOnRefresh: rawConfig.announceOnRefresh === false ? false : DEFAULT_CONFIG.announceOnRefresh,
    cacheMaxAgeMinutes,
    includeSource: rawConfig.includeSource === true
  }
}

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

const THUNDER_PROBABILITY_THRESHOLD = 40
const MEANINGFUL_PRECIPITATION_MM = 0.5
const STRONG_WIND_KPH = 40
const DANGEROUS_HEAT_C = 38

const RAIN_WORDS = ['rain', 'drizzle', 'shower', 'thunder']
const HEAVY_RAIN_WORDS = ['heavy rain', 'torrential']

const includesAny = (text, words) => words.some((word) => String(text || '').toLowerCase().includes(word))

const pointsBetween = (snapshot, period) => {
  if (period.dayOffset) return []
  return (snapshot.hourly || []).filter((point) => (
    Number(point.forecastAtHour || 0) >= period.startHour && Number(point.forecastAtHour || 0) < period.endHour
  ))
}

const rainRisk = (points) => {
  if (!points.length) return 0
  const explicitRain = points.some((point) => includesAny(point.condition, RAIN_WORDS) || includesAny(point.description, RAIN_WORDS))
  const meaningfulPrecipitation = points.some((point) => Number(point.precipitationMm || 0) >= MEANINGFUL_PRECIPITATION_MM)
  const probability = Math.max(...points.map((point) => Number(point.precipitationProbabilityPercent || 0)))
  return Math.max(probability, explicitRain || meaningfulPrecipitation ? 45 : 0)
}

const averageFeels = (points, fallback) => {
  if (!points.length) return fallback
  return Math.round(points.reduce((sum, point) => sum + Number(point.feelsLikeC || fallback), 0) / points.length)
}

const periodSummary = (points, language) => {
  if (!points.length) return language === 'en' ? 'No reliable forecast data' : '暂无可靠数据'
  const representative = [...points].sort((left, right) => Number(right.precipitationProbabilityPercent || 0) - Number(left.precipitationProbabilityPercent || 0))[0]
  const rain = Math.max(...points.map((point) => Number(point.precipitationProbabilityPercent || 0)))
  const feels = averageFeels(points, Number(representative.feelsLikeC || 0))
  if (language === 'en') return `${representative.description}; rain up to ${rain}%; feels like about ${feels}°C`
  return `${representative.description}，降雨概率最高 ${rain}% ，体感约 ${feels}°C`
}

const periodLabel = (label, language) => {
  if (language !== 'en') return label
  return {
    早通勤: 'Morning commute',
    午间: 'Midday',
    晚通勤: 'Evening commute',
    上午: 'Morning',
    下午: 'Afternoon',
    晚上: 'Evening',
    今晚: 'Tonight',
    次日早晨: 'Next morning'
  }[label] || label
}

const umbrella = (primaryRain, middayRain, thunder, language) => {
  if (language === 'en') {
    if (thunder || primaryRain >= 45) return 'Carry a lightweight umbrella'
    if (middayRain >= 20) return 'A midday shower is possible; consider a small umbrella'
    return 'An umbrella is usually unnecessary today'
  }
  if (thunder || primaryRain >= 45) return '建议带一把轻便伞'
  if (middayRain >= 20) return '午间可能有雨，可随手带伞'
  return '今天通常不用带伞'
}

const sunscreen = (uv, language) => {
  if (language === 'en') {
    if (uv >= 8) return `UV ${uv}; use strong protection, seek shade, and reapply outdoors`
    if (uv >= 6) return `UV ${uv}; use sunscreen and seek shade`
    if (uv >= 3) return `UV ${uv}; use normal daily sun protection`
    return `UV ${uv}; no extra sun protection is needed`
  }
  if (uv >= 8) return `UV ${uv}，强烈建议防晒、遮阳，长时间户外注意补涂`
  if (uv >= 6) return `UV ${uv}，建议认真防晒并尽量走阴凉处`
  if (uv >= 3) return `UV ${uv}，建议做好日常防晒`
  return `UV ${uv}，无需特别加强防晒`
}

const clothing = (maxFeels, points, rain, strongWind, language) => {
  const humid = points.some((point) => Number(point.humidityPercent || 0) >= 80)
  if (language === 'en') {
    let text = maxFeels >= 32
      ? 'Wear a breathable light top and lightweight bottoms'
      : maxFeels >= 27
        ? 'Wear short sleeves or a thin shirt with lightweight bottoms'
        : maxFeels >= 22
          ? 'Short sleeves or a thin shirt should be comfortable'
          : 'Bring a light outer layer'
    if (humid) text += '; prefer breathable, quick-drying fabrics'
    if (rain >= 45) text += '; avoid shoes that absorb water easily'
    if (strongWind) text += '; bring a wind-resistant layer and secure loose items'
    return text
  }
  let text = maxFeels >= 32
    ? '短袖或透气薄上衣搭配轻薄下装，注意通风散热'
    : maxFeels >= 27
      ? '短袖或薄衬衫搭配轻薄下装'
      : maxFeels >= 22
        ? '短袖或薄衬衫即可'
        : '建议带一件轻薄外套'
  if (humid) text += '；优先选择透气、易干的面料'
  if (rain >= 45) text += '；避免容易吸水的鞋'
  if (strongWind) text += '；可带防风外层并收好易被吹动的物品'
  return text
}

const subjectFocus = ({ thunder, heavyRain, strongWind, maxFeels, primaryRain, uv, middayRain }, language) => {
  if (language === 'en') {
    if (thunder) return ['[Thunderstorm risk] Weather report', 'Thunderstorms are possible; watch conditions when outside']
    if (heavyRain) return ['[Heavy rain risk] Weather report', 'Heavy rain may affect travel today']
    if (strongWind) return ['[Strong winds today] Weather report', 'Strong winds may affect outdoor activity']
    if (maxFeels >= DANGEROUS_HEAT_C) return ['[Dangerous heat] Weather report', 'It will feel dangerously hot today']
    if (primaryRain >= 45) return ['[Rain likely, carry an umbrella] Weather report', 'Rain is likely during your main outing periods']
    if (maxFeels >= 32) return ['[Hot today, dress lightly] Weather report', 'It will feel hot today; stay ventilated and hydrated']
    if (uv >= 6) return ['[Strong UV, use sun protection] Weather report', 'Midday UV will be strong']
    if (middayRain >= 20) return ['[Possible midday rain] Weather report', 'A brief midday shower is possible']
    return ['[Comfortable weather] Weather report', 'Conditions should remain generally comfortable']
  }
  if (thunder) return ['[雷雨风险，注意安全] 天气早报', '今天有雷雨风险，外出留意天气变化']
  if (heavyRain) return ['[有较强降雨，注意出行] 天气早报', '今天有较强降雨，外出注意积水和路况']
  if (strongWind) return ['[今天风大，注意安全] 天气早报', '今天风力较强，外出注意安全']
  if (maxFeels >= DANGEROUS_HEAT_C) return ['[高温风险，注意防暑] 天气早报', '今天体感炎热，注意防暑降温']
  if (primaryRain >= 45) return ['[通勤有雨，记得带伞] 天气早报', '通勤时段可能有雨']
  if (maxFeels >= 32) return ['[今天闷热，穿轻薄些] 天气早报', '今天体感偏热，注意通风补水']
  if (uv >= 6) return ['[紫外线很强，注意防晒] 天气早报', '午间紫外线较强']
  if (middayRain >= 20) return ['[午间可能有雨] 天气早报', '午间可能有短时降雨']
  return ['[天气舒服，适合出门] 天气早报', '今天整体天气平稳']
}

const closing = ({ thunder, heavyRain, strongWind, maxFeels, rain, uv }, language) => {
  if (language === 'en') {
    if (thunder) return 'Limit outdoor exposure during thunderstorms and travel carefully.'
    if (heavyRain) return 'Watch for standing water and difficult travel conditions.'
    if (strongWind) return 'Watch for falling objects and secure your belongings.'
    if (maxFeels >= DANGEROUS_HEAT_C) return 'Avoid prolonged outdoor activity and keep hydrated.'
    if (rain >= 45) return 'Rain is possible today; take care on the way home.'
    if (maxFeels >= 32) return 'It will be hot today; remember to drink water.'
    if (uv >= 6) return 'Midday sunlight will be strong; remember sun protection.'
    return 'The weather should be comfortable. Have a good day.'
  }
  if (thunder) return '雷雨时尽量减少户外停留，路上注意安全。'
  if (heavyRain) return '今天降雨较强，外出留意积水和路况。'
  if (strongWind) return '今天风力较强，外出注意高空坠物和随身物品。'
  if (maxFeels >= DANGEROUS_HEAT_C) return '今天体感炎热，尽量避开长时间户外活动并及时补水。'
  if (rain >= 45) return '今天可能下雨，回家路上慢一点。'
  if (maxFeels >= 32) return '今天会有些热，记得及时喝水。'
  if (uv >= 6) return '午间阳光强，出门记得做好防晒。'
  return '今天天气还算舒服，祝你一天顺利。'
}

const recommendWeather = (snapshot, options = {}) => {
  const language = options.language === 'en' ? 'en' : 'zh-CN'
  const reportType = options.reportType || 'morning'
  const reportDate = new Date(`${snapshot.daily.date || snapshot.fetchedAt.slice(0, 10)}T00:00:00Z`)
  const schedule = scheduleFor(reportDate, reportType)
  const periodPoints = schedule.map((period) => pointsBetween(snapshot, period))
  const allPoints = periodPoints.flat()
  const primaryPoints = reportType === 'morning' && periodPoints.length >= 3
    ? [...periodPoints[0], ...periodPoints[2]]
    : allPoints
  const middayPoints = reportType === 'morning' && periodPoints.length >= 3
    ? periodPoints[1]
    : allPoints.filter((point) => Number(point.forecastAtHour || 0) >= 1100 && Number(point.forecastAtHour || 0) < 1500)
  const primaryRain = rainRisk(primaryPoints)
  const middayRain = rainRisk(middayPoints)
  const thunder = allPoints.some((point) => Number(point.thunderProbabilityPercent || 0) >= THUNDER_PROBABILITY_THRESHOLD || includesAny(point.condition, ['thunder']))
  const heavyRain = allPoints.some((point) => includesAny(point.condition, HEAVY_RAIN_WORDS) || includesAny(point.description, HEAVY_RAIN_WORDS))
  const strongestWind = Math.max(Number(snapshot.current.windSpeedKph || 0), ...allPoints.map((point) => Number(point.windSpeedKph || 0)))
  const strongWind = strongestWind >= STRONG_WIND_KPH
  const uv = Math.max(Number(snapshot.daily.uvIndex || 0), ...middayPoints.map((point) => Number(point.uvIndex || 0)))
  const maxFeels = Math.max(Number(snapshot.current.feelsLikeC || 0), ...allPoints.map((point) => Number(point.feelsLikeC || 0)))
  const rain = Math.max(primaryRain, middayRain)
  const [subject, focus] = subjectFocus({ thunder, heavyRain, strongWind, maxFeels, primaryRain, uv, middayRain }, language)

  return {
    schemaVersion: 1,
    subject,
    focus,
    umbrella: umbrella(primaryRain, middayRain, thunder, language),
    sunscreen: sunscreen(uv, language),
    clothing: clothing(maxFeels, allPoints, rain, strongWind, language),
    closing: closing({ thunder, heavyRain, strongWind, maxFeels, rain, uv }, language),
    periods: schedule.map((period, index) => ({
      label: periodLabel(period.label, language),
      summary: periodSummary(periodPoints[index] || [], language)
    })),
    signals: {
      highestRiskLevel: thunder || heavyRain ? 3 : strongWind || maxFeels >= DANGEROUS_HEAT_C ? 2 : 0,
      umbrellaLevel: thunder || primaryRain >= 45 ? 2 : middayRain >= 20 ? 1 : 0,
      sunscreenLevel: uv >= 8 ? 3 : uv >= 6 ? 2 : uv >= 3 ? 1 : 0,
      clothingLevel: maxFeels >= 32 ? 3 : maxFeels >= 27 ? 2 : maxFeels >= 22 ? 1 : 0,
      targetPrecipitationLevel: rain >= 45 ? 2 : rain >= 20 ? 1 : 0,
      thunderstorm: thunder,
      strongWind,
      dangerousHeat: maxFeels >= DANGEROUS_HEAT_C
    }
  }
}

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

const cloneJson = (value) => JSON.parse(JSON.stringify(value))

const isFresh = (snapshot, maxAgeMinutes) => {
  const ageMs = Date.now() - new Date(snapshot.fetchedAt).getTime()
  return Number.isFinite(ageMs) && ageMs <= maxAgeMinutes * 60 * 1000
}

const readCache = async (ctx) => {
  const snapshot = await ctx.storage.get('last:snapshot', null)
  const advice = await ctx.storage.get('last:advice', null)
  const summary = await ctx.storage.get('last:summary', '')
  const detail = await ctx.storage.get('last:detail', '')
  const error = await ctx.storage.get('last:error', null)
  return { snapshot, advice, summary, detail, error }
}

const normalizeStats = (stats = {}) => ({
  refreshCount: Number(stats.refreshCount || 0),
  announceCount: Number(stats.announceCount || 0),
  lastSuccessAt: stats.lastSuccessAt || null,
  lastFailureAt: stats.lastFailureAt || null
})

const readStats = async (ctx) => normalizeStats(await ctx.storage.get('stats', {}))

const updateStats = async (ctx, updater) => {
  const nextStats = normalizeStats(updater(await readStats(ctx)))
  await ctx.storage.set('stats', nextStats)
  return nextStats
}

const writeCache = async (ctx, payload) => {
  await ctx.storage.set('state:schemaVersion', 1)
  await ctx.storage.set('last:snapshot', payload.snapshot)
  await ctx.storage.set('last:advice', payload.advice)
  await ctx.storage.set('last:summary', payload.summary)
  await ctx.storage.set('last:detail', payload.detail)
  await ctx.storage.set('last:error', null)
  await ctx.storage.set('stats', payload.stats)
}

const writeProviderError = async (ctx, error) => {
  const failedAt = new Date().toISOString()
  await ctx.storage.set('last:error', {
    message: error.message,
    at: failedAt,
    providerHosts: ['wttr.in', 'wttr.is']
  })
  await updateStats(ctx, (stats) => ({
    ...stats,
    lastFailureAt: failedAt
  }))
}

const sayAndCount = async (ctx, message) => {
  await ctx.pet.say(message)
  await updateStats(ctx, (stats) => ({
    ...stats,
    announceCount: stats.announceCount + 1
  }))
}

const buildReport = (snapshot, config, { cached = false } = {}) => {
  const advice = recommendWeather(snapshot, {
    language: config.language,
    reportType: config.reportType
  })
  const rendered = renderWeatherText(snapshot, advice, {
    language: config.language,
    includeSource: config.includeSource,
    cached
  })
  return {
    ok: true,
    cached,
    source: snapshot.source.host,
    fetchedAt: snapshot.fetchedAt,
    summary: rendered.summary,
    detail: rendered.detail,
    snapshot: cloneJson(snapshot),
    advice: cloneJson(advice),
    warnings: []
  }
}

const fetchFreshReport = async (ctx, config) => {
  const snapshot = await fetchWeatherSnapshot({
    locationName: config.locationName,
    locationQuery: config.locationQuery,
    fetchedAt: new Date().toISOString(),
    fetchImpl: ctx.network.fetch
  })
  const report = buildReport(snapshot, config)
  const stats = await readStats(ctx)
  await writeCache(ctx, {
    snapshot,
    advice: report.advice,
    summary: report.summary,
    detail: report.detail,
    stats: {
      refreshCount: stats.refreshCount + 1,
      announceCount: stats.announceCount,
      lastSuccessAt: snapshot.fetchedAt,
      lastFailureAt: stats.lastFailureAt
    }
  })
  return report
}

const withFallbackCache = async (ctx, config, fetchError) => {
  const cache = await readCache(ctx)
  if (cache.snapshot && isFresh(cache.snapshot, config.cacheMaxAgeMinutes)) {
    const report = buildReport(cache.snapshot, config, { cached: true })
    report.summary = cache.summary || report.summary
    report.detail = cache.detail || report.detail
    report.warnings = [fetchError.message]
    await writeProviderError(ctx, fetchError)
    return report
  }
  await writeProviderError(ctx, fetchError)
  throw fetchError
}

const createCommands = (ctx) => {
  const getConfig = () => normalizeConfig(ctx.config.get())

  const fetchReportWithCache = async () => {
    const config = getConfig()
    try {
      return await fetchFreshReport(ctx, config)
    } catch (error) {
      return await withFallbackCache(ctx, config, error)
    }
  }

  const handleRefresh = async () => {
    const config = getConfig()
    const report = await fetchReportWithCache()
    if (config.announceOnRefresh || report.cached) {
      await sayAndCount(ctx, report.summary)
    }
    return report
  }

  return {
    refresh: handleRefresh,
    announce: async () => {
      const report = await fetchReportWithCache()
      await sayAndCount(ctx, report.summary)
      return report
    },
    last: async () => {
      const cache = await readCache(ctx)
      if (!cache.snapshot && !cache.summary) {
        const config = getConfig()
        await ctx.pet.say(config.language === 'en' ? 'No cached weather report yet.' : '还没有缓存天气，先刷新一次吧。')
        return { ok: false, reason: 'missing-cache' }
      }
      if (cache.summary) {
        await sayAndCount(ctx, cache.summary)
        return { ok: true, cached: true, summary: cache.summary, detail: cache.detail || '' }
      }
      const config = getConfig()
      const report = buildReport(cache.snapshot, config, { cached: true })
      await sayAndCount(ctx, report.summary)
      return report
    },
    status: async () => {
      const config = getConfig()
      const cache = await readCache(ctx)
      return {
        ok: true,
        hasCache: Boolean(cache.snapshot),
        cachedAt: cache.snapshot?.fetchedAt || null,
        lastError: cache.error,
        config: cloneJson(config)
      }
    },
    'clear-cache': async () => {
      await ctx.storage.clear()
      return { ok: true, cleared: true }
    },
    cleanup: async (input = {}) => {
      const confirmed = input.confirm === true
      if (confirmed) {
        await ctx.storage.clear()
      }
      return {
        ok: true,
        dryRun: !confirmed,
        clearedStorage: confirmed,
        cleanupSurface: 'compat-main',
        message: confirmed
          ? 'Compatibility cleanup cleared OpenPet command-plugin storage. Service-owned file cleanup is handled by the unified shell cleanup command.'
          : 'Compatibility cleanup dry run. Re-run with { confirm: true } to clear OpenPet command-plugin storage.'
      }
    }
  }
}

module.exports = function activate(ctx) {
  return createCommands(ctx)
}

