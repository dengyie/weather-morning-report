const { readFileSync } = require('node:fs')
const path = require('node:path')
const fastify = require('fastify')
const { ensureServicePaths } = require('./paths')
const { validateBranding, validateDefaults, validateManualPreview, validateNotifications, validateRecipient, validateSchedule, validateSmtp } = require('./configuration/validation')
const { loadConfiguration, readRecentLogs, saveConfiguration } = require('./storage/configuration-store')
const { renderConfigurationPage } = require('./views/configuration')
const { renderDashboardPage } = require('./views/dashboard')
const { renderLogsPage } = require('./views/logs')
const { renderManualPreviewPage } = require('./views/manual-preview')
const { version } = require('../package.json')

const createServiceApp = ({ env = process.env } = {}) => {
  const paths = ensureServicePaths(env)
  const app = fastify({ logger: false })

  app.addContentTypeParser('application/x-www-form-urlencoded', { parseAs: 'string' }, (_request, body, done) => {
    done(null, Object.fromEntries(new URLSearchParams(body || '')))
  })

  app.get('/health', async () => ({
    ok: true,
    service: 'weather-morning-report',
    framework: 'fastify',
    version,
    directories: {
      data: Boolean(paths.dataDir),
      cache: Boolean(paths.cacheDir),
      logs: Boolean(paths.logDir)
    }
  }))

  app.get('/', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    reply.type('text/html; charset=utf-8')
    return renderDashboardPage({ configuration })
  })

  app.get('/configuration', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    reply.type('text/html; charset=utf-8')
    return renderConfigurationPage({ configuration })
  })

  app.get('/logs', async (_request, reply) => {
    const lines = readRecentLogs(paths, 50)
    reply.type('text/html; charset=utf-8')
    return renderLogsPage({ lines })
  })

  app.post('/configuration/recipients', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateRecipient(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { recipient: result.values } })
    }
    const id = result.value.id || `recipient-${configuration.recipients.length + 1}`
    const recipient = { ...result.value, id }
    configuration.recipients = configuration.recipients.filter((item) => item.id !== id).concat(recipient)
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/defaults', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateDefaults(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { defaults: result.values } })
    }
    configuration.newUserDefaults = result.value
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/schedules', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateSchedule(request.body, configuration)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { schedule: result.values } })
    }
    const id = result.value.id || `schedule-${configuration.schedules.length + 1}`
    const schedule = { ...result.value, id }
    configuration.schedules = configuration.schedules.filter((item) => item.id !== id).concat(schedule)
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/smtp', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateSmtp(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { smtp: result.values } })
    }
    configuration.smtp = {
      host: result.value.host,
      port: result.value.port,
      username: result.value.username,
      security: result.value.security,
      senderEmail: result.value.senderEmail,
      passwordSaved: configuration.smtp.passwordSaved || result.value.password.length > 0
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/branding', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateBranding(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { branding: result.values } })
    }
    configuration.branding = result.value
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/notifications', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateNotifications(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors, values: { notifications: result.values } })
    }
    configuration.notifications = result.value
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/manual/preview', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateManualPreview(request.body, configuration)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: result.errors })
    }
    reply.type('text/html; charset=utf-8')
    return renderManualPreviewPage({ recipient: result.value.recipient, reportType: result.value.reportType })
  })

  app.get('/static/app.css', async (_request, reply) => {
    reply.type('text/css; charset=utf-8')
    return readFileSync(path.join(__dirname, '..', 'static', 'app.css'), 'utf8')
  })

  return app
}

module.exports = { createServiceApp }
