const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const { createDefaultConfiguration } = require('../configuration/defaults')

const configurationPath = (paths) => path.join(paths.dataDir, 'configuration.json')

const mergeConfiguration = (configuration) => {
  const defaults = createDefaultConfiguration()
  return {
    ...defaults,
    ...configuration,
    newUserDefaults: { ...defaults.newUserDefaults, ...configuration.newUserDefaults },
    smtp: { ...defaults.smtp, ...configuration.smtp },
    branding: { ...defaults.branding, ...configuration.branding },
    notifications: { ...defaults.notifications, ...configuration.notifications },
    providers: Array.isArray(configuration.providers) ? configuration.providers : defaults.providers,
    recipients: Array.isArray(configuration.recipients) ? configuration.recipients : defaults.recipients,
    schedules: Array.isArray(configuration.schedules) ? configuration.schedules : defaults.schedules
  }
}

const saveConfiguration = (paths, configuration) => {
  mkdirSync(paths.dataDir, { recursive: true })
  writeFileSync(configurationPath(paths), `${JSON.stringify(mergeConfiguration(configuration), null, 2)}\n`)
}

const loadConfiguration = (paths) => {
  const file = configurationPath(paths)
  if (!existsSync(file)) {
    const configuration = createDefaultConfiguration()
    saveConfiguration(paths, configuration)
    return configuration
  }

  const configuration = mergeConfiguration(JSON.parse(readFileSync(file, 'utf8')))
  saveConfiguration(paths, configuration)
  return configuration
}

const readRecentLogs = (paths, limit = 50) => {
  const file = path.join(paths.logDir, 'service.log')
  if (!existsSync(file)) {
    return []
  }
  return readFileSync(file, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-limit)
}

module.exports = { configurationPath, loadConfiguration, readRecentLogs, saveConfiguration }
