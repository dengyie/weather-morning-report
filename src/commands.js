const { fetchWeatherSnapshot } = require('./weather-provider')
const { normalizeConfig } = require('./config')
const { recommendWeather } = require('./recommendation-engine')
const { renderWeatherText } = require('./text-renderer')

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
    }
  }
}

module.exports = { createCommands }
