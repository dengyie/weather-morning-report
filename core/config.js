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

module.exports = { DEFAULT_CONFIG, normalizeConfig }
