const { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const { normalizeConfig } = require('../core/config')
const { fetchWeatherSnapshot } = require('../core/weather-provider')
const { recommendWeather } = require('../core/recommendation-engine')
const { renderWeatherText } = require('../rendering/text-renderer')
const { extensionEnv } = require('./runner')

const cacheFile = (env) => {
  const directory = env.OPENPET_CACHE_DIR || env.OPENPET_DATA_DIR
  return directory ? path.join(directory, 'weather-command-cache.json') : null
}

const readCache = (env) => {
  const file = cacheFile(env)
  if (!file || !existsSync(file)) return {}
  return JSON.parse(readFileSync(file, 'utf8'))
}

const writeCache = (env, payload) => {
  const file = cacheFile(env)
  if (!file) return
  mkdirSync(path.dirname(file), { recursive: true })
  writeFileSync(file, `${JSON.stringify(payload, null, 2)}\n`)
}

const clearCache = (env) => {
  const file = cacheFile(env)
  if (file) rmSync(file, { force: true })
}

const cloneJson = (value) => JSON.parse(JSON.stringify(value))

const fetchImplFor = (input) => {
  if (input.weatherPayload) {
    return async () => ({ ok: true, status: 200, text: JSON.stringify(input.weatherPayload) })
  }
  if (typeof fetch !== 'function') {
    throw new Error('global fetch is unavailable and no weatherPayload fixture was provided')
  }
  return async (url, options) => {
    const response = await fetch(url, options)
    return { ok: response.ok, status: response.status, text: await response.text() }
  }
}

const buildReport = (snapshot, config, { command, input, env, cached = false } = {}) => {
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
    command,
    input,
    env: extensionEnv(env),
    cached,
    source: snapshot.source.host,
    fetchedAt: snapshot.fetchedAt,
    summary: rendered.summary,
    detail: rendered.detail,
    snapshot: cloneJson(snapshot),
    advice: cloneJson(advice)
  }
}

const refreshReport = async ({ command, input, env }) => {
  const config = normalizeConfig(input)
  const snapshot = await fetchWeatherSnapshot({
    locationName: config.locationName,
    locationQuery: config.locationQuery,
    fetchedAt: new Date().toISOString(),
    fetchImpl: fetchImplFor(input)
  })
  const report = buildReport(snapshot, config, { command, input, env })
  writeCache(env, {
    snapshot: report.snapshot,
    advice: report.advice,
    summary: report.summary,
    detail: report.detail,
    config,
    fetchedAt: report.fetchedAt
  })
  return report
}

const announceReport = async ({ command, input, env }) => refreshReport({ command, input, env })

const lastReport = ({ command, input, env }) => {
  const cache = readCache(env)
  if (!cache.snapshot && !cache.summary) {
    return {
      ok: false,
      command,
      input,
      env: extensionEnv(env),
      reason: 'missing-cache'
    }
  }
  if (cache.summary) {
    return {
      ok: true,
      command,
      input,
      env: extensionEnv(env),
      cached: true,
      summary: cache.summary,
      detail: cache.detail || '',
      fetchedAt: cache.fetchedAt || cache.snapshot?.fetchedAt || null
    }
  }
  return buildReport(cache.snapshot, normalizeConfig(cache.config || input), { command, input, env, cached: true })
}

const statusReport = ({ command, input, env }) => {
  const cache = readCache(env)
  return {
    ok: true,
    command,
    input,
    env: extensionEnv(env),
    hasCache: Boolean(cache.snapshot || cache.summary),
    cachedAt: cache.fetchedAt || cache.snapshot?.fetchedAt || null,
    config: normalizeConfig(cache.config || input)
  }
}

const clearCommandCache = ({ command, input, env }) => {
  clearCache(env)
  return {
    ok: true,
    command,
    input,
    env: extensionEnv(env),
    cleared: true
  }
}

module.exports = { announceReport, clearCommandCache, lastReport, refreshReport, statusReport }
