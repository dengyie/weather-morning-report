const { scheduleFor } = require('./period-schedule')

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

module.exports = {
  DANGEROUS_HEAT_C,
  MEANINGFUL_PRECIPITATION_MM,
  STRONG_WIND_KPH,
  THUNDER_PROBABILITY_THRESHOLD,
  recommendWeather
}
