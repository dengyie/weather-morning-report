const { readFileSync } = require('node:fs')
const path = require('node:path')
const fastify = require('fastify')
const { renderEmailReport } = require('../rendering/email-renderer')
const { ensureServicePaths } = require('./paths')
const { validateBranding, validateDefaults, validateManualPreview, validateNotifications, validateRecipient, validateSchedule, validateSmtp } = require('./configuration/validation')
const { defaultFetchReport, redactError, sendEmailNow } = require('./email/send-now')
const { createSmtpEmailTransport } = require('./email/transports')
const { loadConfiguration, readRecentLogs, saveConfiguration } = require('./storage/configuration-store')
const { renderConfigurationPage } = require('./views/configuration')
const { renderDashboardPage } = require('./views/dashboard')
const { renderEmailPreviewPage } = require('./views/email-preview')
const { renderLogsPage } = require('./views/logs')
const { renderManualPreviewPage } = require('./views/manual-preview')
const { renderSchedulerPage } = require('./views/scheduler')
const { enqueueDueJobs, queueStatus } = require('./scheduler/queue')
const { version } = require('../package.json')

const findRecipient = (configuration, recipientId) => configuration.recipients
  .find((recipient) => recipient.id === recipientId && !recipient.archivedAt)

const configuredSmtpSender = (smtp = {}) => {
  const senderEmail = String(smtp.senderEmail || smtp.username || '').trim()
  if (!senderEmail) throw new Error('SMTP sender email is required')
  return senderEmail
}

const createServiceApp = ({
  env = process.env,
  emailTransport,
  createEmailTransport = createSmtpEmailTransport,
  fetchEmailReport = defaultFetchReport,
  schedulerNow = () => new Date()
} = {}) => {
  const paths = ensureServicePaths(env)
  const resolvedEmailTransport = emailTransport || createEmailTransport({ env })
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

  app.get('/scheduler', async (_request, reply) => {
    const status = queueStatus(paths, { now: schedulerNow() })
    reply.type('text/html; charset=utf-8')
    return renderSchedulerPage({ status })
  })

  app.post('/scheduler/enqueue-due', async (_request, reply) => {
    const now = schedulerNow()
    const created = enqueueDueJobs(paths, { now })
    return reply.code(200).send({
      ok: true,
      created,
      status: queueStatus(paths, { now })
    })
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

  app.post('/configuration/smtp/test-connection', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    try {
      if (typeof resolvedEmailTransport.verify !== 'function') {
        throw new Error('SMTP transport does not support connection verification')
      }
      const senderEmail = configuredSmtpSender(configuration.smtp)
      await resolvedEmailTransport.verify({
        envelope: {
          from: senderEmail
        },
        smtp: configuration.smtp
      })
      return reply.code(200).send({ ok: true, status: 'connected' })
    } catch (error) {
      return reply.code(502).send({ ok: false, error: redactError(error, [env.SMTP_PASSWORD]) })
    }
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

  app.get('/email/preview', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const recipientId = String(request.query?.recipient_id || '')
    const reportType = String(request.query?.report_type || 'morning')
    const recipient = findRecipient(configuration, recipientId)
    if (!recipient) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfigurationPage({ configuration, errors: ['收件人不存在'] })
    }
    try {
      const report = await fetchEmailReport({ recipient, reportType, configuration })
      const rendered = renderEmailReport({
        snapshot: report.snapshot,
        advice: report.advice,
        recipient,
        branding: configuration.branding,
        reportType,
        cached: report.cached
      })
      reply.type('text/html; charset=utf-8')
      return renderEmailPreviewPage({ rendered, recipient })
    } catch (error) {
      return reply.code(502).send({ ok: false, error: redactError(error, [env.SMTP_PASSWORD]) })
    }
  })

  app.post('/email/send-now', async (request, reply) => {
    try {
      const result = await sendEmailNow({
        paths,
        recipientId: request.body?.recipient_id,
        reportType: request.body?.report_type || 'morning',
        transport: resolvedEmailTransport,
        fetchReport: fetchEmailReport,
        secrets: [env.SMTP_PASSWORD]
      })
      return result.ok
        ? reply.code(200).send(result)
        : reply.code(502).send(result)
    } catch (error) {
      if (error.message === '收件人不存在') {
        return reply.code(400).send({ ok: false, error: error.message })
      }
      return reply.code(502).send({ ok: false, error: redactError(error, [env.SMTP_PASSWORD]) })
    }
  })

  app.post('/email/test', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const recipient = findRecipient(configuration, request.body?.recipient_id)
    if (!recipient) {
      return reply.code(400).send({ ok: false, error: '收件人不存在' })
    }
    try {
      const senderEmail = configuredSmtpSender(configuration.smtp)
      const delivery = await resolvedEmailTransport.send({
        envelope: {
          from: senderEmail,
          to: recipient.email
        },
        smtp: configuration.smtp,
        subject: 'Weather Morning Report SMTP test',
        text: 'Weather Morning Report SMTP test message. If you received this, Email delivery is configured.',
        html: '<p>Weather Morning Report SMTP test message.</p><p>If you received this, Email delivery is configured.</p>'
      })
      return reply.code(200).send({ ok: true, status: 'sent', messageId: delivery?.messageId || 'smtp-test' })
    } catch (error) {
      return reply.code(502).send({ ok: false, error: redactError(error, [env.SMTP_PASSWORD]) })
    }
  })

  app.get('/static/app.css', async (_request, reply) => {
    reply.type('text/css; charset=utf-8')
    return readFileSync(path.join(__dirname, '..', 'static', 'app.css'), 'utf8')
  })

  return app
}

module.exports = { createServiceApp }
