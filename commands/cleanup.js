const { existsSync, rmSync } = require('node:fs')
const path = require('node:path')
const { resolveServicePaths } = require('../service/paths')
const { runJsonCommand } = require('./runner')

const cleanupTargets = (env) => {
  const paths = resolveServicePaths(env)
  const commandCacheDir = env.OPENPET_CACHE_DIR || env.OPENPET_DATA_DIR || paths.cacheDir
  return [
    { id: 'configuration', file: path.join(paths.dataDir, 'configuration.json') },
    { id: 'delivery-history', file: path.join(paths.dataDir, 'delivery-history.json') },
    { id: 'scheduler-state', file: path.join(paths.dataDir, 'scheduler-state.json') },
    { id: 'command-cache', file: path.join(commandCacheDir, 'weather-command-cache.json') },
    { id: 'service-log', file: path.join(paths.logDir, 'service.log') }
  ]
}

const runCleanup = ({ command, input, env }) => {
  const confirmed = input.confirm === true
  const planned = cleanupTargets(env).map((target) => ({
    ...target,
    exists: existsSync(target.file)
  }))
  const deleted = []

  if (confirmed) {
    for (const target of planned) {
      if (!target.exists) continue
      rmSync(target.file, { force: true })
      deleted.push(target)
    }
  }

  return {
    ok: true,
    command,
    input,
    dryRun: !confirmed,
    planned,
    deleted,
    message: confirmed
      ? 'Removed known Weather Morning Report service-owned files. External accounts and third-party-managed data are untouched.'
      : 'Dry run only. Re-run with {"confirm":true} to remove known Weather Morning Report service-owned files.'
  }
}

runJsonCommand('cleanup', runCleanup)

module.exports = { cleanupTargets, runCleanup }
