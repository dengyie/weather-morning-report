const { mkdirSync } = require('node:fs')
const path = require('node:path')

const defaultBaseDir = () => path.join(process.cwd(), 'var', 'weather-morning-report')

const resolveServicePaths = (env = process.env) => {
  const baseDir = env.OPENPET_DATA_DIR || defaultBaseDir()
  return {
    dataDir: baseDir,
    cacheDir: env.OPENPET_CACHE_DIR || path.join(baseDir, 'cache'),
    logDir: env.OPENPET_LOG_DIR || path.join(baseDir, 'logs')
  }
}

const ensureServicePaths = (env = process.env) => {
  const paths = resolveServicePaths(env)
  for (const directory of Object.values(paths)) {
    mkdirSync(directory, { recursive: true })
  }
  return paths
}

module.exports = { ensureServicePaths, resolveServicePaths }
