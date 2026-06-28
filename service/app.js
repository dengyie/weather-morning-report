const { readFileSync } = require('node:fs')
const path = require('node:path')
const fastify = require('fastify')
const { renderEmailReport } = require('../rendering/email-renderer')
const { ensureServicePaths } = require('./paths')
const { validateBranding, validateDefaults, validateManualPreview, validateNotifications, validateRecipient, validateSchedule, validateSmtp } = require('./configuration/validation')
const { defaultFetchReport, redactError, sendEmailNow } = require('./email/send-now')
const { createSmtpEmailTransport } = require('./email/transports')
const { loadConfiguration, readRecentLogs, saveConfiguration } = require('./storage/configuration-store')
const {
  clearStoredSmtpPassword,
  hasStoredSmtpPassword,
  inspectSecretHealth,
  loadStoredSmtpPassword,
  rotateStoredSmtpPasswordKey,
  saveStoredSmtpPassword
} = require('./storage/secret-store')
const {
  appendSmtpOperationHistory,
  listSmtpOperationHistory,
  loadSmtpOperationHistory,
  serializeSmtpOperationHistoryCsv
} = require('./storage/smtp-operation-history-store')
const { renderConfigurationPage } = require('./views/configuration')
const { renderDashboardPage } = require('./views/dashboard')
const { renderEmailPreviewPage } = require('./views/email-preview')
const { renderLogsPage } = require('./views/logs')
const { renderManualPreviewPage } = require('./views/manual-preview')
const { renderSchedulerPage } = require('./views/scheduler')
const { enqueueDueJobs, queueStatus } = require('./scheduler/queue')
const { dashboardAuthEnabled, ensureDashboardToken, verifyDashboardToken } = require('./dashboard-auth')
const { version } = require('../package.json')

const findRecipient = (configuration, recipientId) => configuration.recipients
  .find((recipient) => recipient.id === recipientId && !recipient.archivedAt)

const configuredSmtpSender = (smtp = {}) => {
  const senderEmail = String(smtp.senderEmail || smtp.username || '').trim()
  if (!senderEmail) throw new Error('SMTP sender email is required')
  return senderEmail
}

const isConfigurationPageMode = (body = {}) => body?.page_mode === 'configuration'

const configurationNoticeLocation = (message) => `/configuration?smtp_notice=${encodeURIComponent(message)}`

const smtpOperationHistoryFiltersFromQuery = (query = {}) => ({
  action: query.smtp_action,
  status: query.smtp_status,
  recipientId: query.smtp_recipient_id
})

const smtpStateForView = (configuration, { hasManagedPassword = false } = {}) => ({
  ...configuration.smtp,
  passwordSaved: configuration.smtp.passwordSaved || hasManagedPassword,
  hasManagedPassword
})

const configurationForView = (configuration, smtpState) => ({
  ...configuration,
  smtp: smtpState
})

const configurationViewModel = (configuration, { hasManagedPassword = false, secretHealth } = {}) => ({
  ...configurationForView(configuration, smtpStateForView(configuration, { hasManagedPassword })),
  secretHealth
})

const withResolvedPassword = (smtp, password) => {
  const runtimeSmtp = { ...smtp, passwordSaved: true }
  Object.defineProperty(runtimeSmtp, 'resolvedPassword', {
    value: password,
    enumerable: false,
    configurable: true,
    writable: false
  })
  return runtimeSmtp
}

const loadStoredPasswordOrThrow = (paths) => {
  const stored = loadStoredSmtpPassword(paths)
  return stored || null
}

const safeLoadStoredPassword = (paths) => {
  try {
    return loadStoredSmtpPassword(paths)
  } catch {
    return null
  }
}

const resolveRuntimeSmtp = (paths, configuration, { includeResolvedPassword = true } = {}) => {
  const hasManagedPassword = hasStoredSmtpPassword(paths)
  const stored = hasManagedPassword ? loadStoredPasswordOrThrow(paths) : null
  return {
    smtp: stored
      ? (includeResolvedPassword
          ? withResolvedPassword(configuration.smtp, stored.password)
          : { ...configuration.smtp, passwordSaved: true })
      : configuration.smtp,
    secrets: stored ? [stored.password] : [],
    hasManagedPassword
  }
}

let smtpOperationSequence = 0

const createSmtpOperationRecord = ({ action, status, recipient, messageId, error, now = new Date() }) => {
  smtpOperationSequence += 1
  return {
    id: `smtp-operation-${now.toISOString().replace(/[:.]/g, '-')}-${smtpOperationSequence}`,
    createdAt: now.toISOString(),
    action,
    status,
    ...(recipient
      ? {
          recipientId: recipient.id,
          recipientEmail: recipient.email,
          recipientName: recipient.name
        }
      : {}),
    ...(messageId ? { messageId } : {}),
    ...(error ? { error } : {})
  }
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
  const allowResolvedPassword = !emailTransport
  const dashboardToken = dashboardAuthEnabled(env) ? ensureDashboardToken(paths) : ''
  const app = fastify({ logger: false })

  const secretHealthForView = (configuration) => inspectSecretHealth(paths, {
    backupConfirmed: configuration.notifications.secretKeyBackupConfirmed
  })

  const configurationModelForView = (configuration, { hasManagedPassword, secretHealth } = {}) => {
    const resolvedSecretHealth = secretHealth || secretHealthForView(configuration)
    const resolvedHasManagedPassword = typeof hasManagedPassword === 'boolean'
      ? hasManagedPassword
      : resolvedSecretHealth.managedSmtpPassword.present
    return configurationViewModel(configuration, {
      hasManagedPassword: resolvedHasManagedPassword,
      secretHealth: resolvedSecretHealth
    })
  }

  app.addContentTypeParser('application/x-www-form-urlencoded', { parseAs: 'string' }, (_request, body, done) => {
    done(null, Object.fromEntries(new URLSearchParams(body || '')))
  })

  app.addHook('preHandler', async (request, reply) => {
    if (!dashboardAuthEnabled(env) || !['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) return
    if (verifyDashboardToken(request, dashboardToken)) return
    return reply.code(403).send({ ok: false, error: 'Dashboard token is required' })
  })

  const renderConfiguration = (options) => renderConfigurationPage({
    dashboardToken,
    ...options
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
    return renderDashboardPage({ configuration, dashboardToken })
  })

  app.get('/configuration', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    const secretHealth = secretHealthForView(configuration)
    const { filters, records } = listSmtpOperationHistory(paths, smtpOperationHistoryFiltersFromQuery(_request.query), {
      allowedRecipientIds: configuration.recipients.map((recipient) => recipient.id)
    })
    reply.type('text/html; charset=utf-8')
    const notice = String(_request.query?.smtp_notice || '').trim()
    return renderConfiguration({
      configuration: configurationModelForView(configuration, { secretHealth }),
      notices: notice ? [notice] : [],
      smtpOperations: records,
      smtpHistoryFilters: filters
    })
  })

  app.get('/configuration/smtp/history/export', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const { filters, records } = listSmtpOperationHistory(paths, smtpOperationHistoryFiltersFromQuery(request.query), {
      allowedRecipientIds: configuration.recipients.map((recipient) => recipient.id)
    })
    const format = String(request.query?.format || '').trim().toLowerCase()

    if (format === 'json') {
      return reply
        .type('application/json; charset=utf-8')
        .code(200)
        .send({ ok: true, filters, records })
    }

    if (format === 'csv') {
      return reply
        .type('text/csv; charset=utf-8')
        .header('content-disposition', 'attachment; filename="smtp-operational-history.csv"')
        .code(200)
        .send(serializeSmtpOperationHistoryCsv(records))
    }

    return reply.code(400).send({ ok: false, error: 'Unsupported SMTP history export format' })
  })

  app.get('/logs', async (_request, reply) => {
    const lines = readRecentLogs(paths, 50)
    reply.type('text/html; charset=utf-8')
    return renderLogsPage({ lines })
  })

  app.get('/scheduler', async (_request, reply) => {
    const status = queueStatus(paths, { now: schedulerNow() })
    reply.type('text/html; charset=utf-8')
    return renderSchedulerPage({ status, dashboardToken })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors, values: { recipient: result.values } })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors, values: { defaults: result.values } })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors, values: { schedule: result.values } })
    }
    const id = result.value.id || `schedule-${configuration.schedules.length + 1}`
    const schedule = { ...result.value, id }
    configuration.schedules = configuration.schedules.filter((item) => item.id !== id).concat(schedule)
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/smtp', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const secretHealth = secretHealthForView(configuration)
    const managedPasswordPresent = secretHealth.managedSmtpPassword.present
    const result = validateSmtp(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfiguration({
        configuration: configurationModelForView(configuration, {
          hasManagedPassword: managedPasswordPresent,
          secretHealth
        }),
        errors: result.errors,
        values: {
          smtp: {
            ...smtpStateForView(configuration, { hasManagedPassword: managedPasswordPresent }),
            ...result.values
          }
        }
      })
    }
    if (result.value.password.length > 0) {
      saveStoredSmtpPassword(paths, result.value.password)
    }
    configuration.smtp = {
      host: result.value.host,
      port: result.value.port,
      username: result.value.username,
      security: result.value.security,
      senderEmail: result.value.senderEmail,
      passwordSaved: configuration.smtp.passwordSaved || managedPasswordPresent || result.value.password.length > 0
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/smtp/clear-password', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    clearStoredSmtpPassword(paths)
    configuration.smtp = {
      ...configuration.smtp,
      passwordSaved: false
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/secrets/confirm-backup', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    configuration.notifications = {
      ...configuration.notifications,
      secretKeyBackupConfirmed: true
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/secrets/revoke-backup-confirmation', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    configuration.notifications = {
      ...configuration.notifications,
      secretKeyBackupConfirmed: false
    }
    saveConfiguration(paths, configuration)
    return reply.code(303).header('location', '/configuration').send()
  })

  app.post('/configuration/secrets/rotate-key', async (_request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = rotateStoredSmtpPasswordKey(paths, {
      onRotated: () => {
        configuration.notifications = {
          ...configuration.notifications,
          secretKeyBackupConfirmed: false
        }
        saveConfiguration(paths, configuration)
      }
    })
    if (!result.ok) {
      reply.code(502).type('text/html; charset=utf-8')
      return renderConfiguration({
        configuration: configurationModelForView(configuration),
        errors: [result.error]
      })
    }
    return reply.code(303).header('location', '/configuration?smtp_notice=' + encodeURIComponent('本地密钥已轮换，请重新确认新密钥的备份状态')).send()
  })

  app.post('/configuration/smtp/test-connection', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const pageMode = isConfigurationPageMode(request.body)
    try {
      if (typeof resolvedEmailTransport.verify !== 'function') {
        throw new Error('SMTP transport does not support connection verification')
      }
      const { smtp, hasManagedPassword } = resolveRuntimeSmtp(paths, configuration, {
        includeResolvedPassword: allowResolvedPassword
      })
      const senderEmail = configuredSmtpSender(configuration.smtp)
      await resolvedEmailTransport.verify({
        envelope: {
          from: senderEmail
        },
        smtp
      })
      appendSmtpOperationHistory(paths, createSmtpOperationRecord({
        action: 'test-connection',
        status: 'connected'
      }))
      if (pageMode) {
        return reply.code(303).header('location', configurationNoticeLocation('SMTP connection verified.')).send()
      }
      return reply.code(200).send({ ok: true, status: 'connected' })
    } catch (error) {
      const managedPasswordPresent = hasStoredSmtpPassword(paths)
      const redacted = redactError(error, [env.SMTP_PASSWORD, ...(managedPasswordPresent ? [safeLoadStoredPassword(paths)?.password].filter(Boolean) : [])])
      appendSmtpOperationHistory(paths, createSmtpOperationRecord({
        action: 'test-connection',
        status: 'failed',
        error: redacted
      }))
      if (pageMode) {
        reply.code(502).type('text/html; charset=utf-8')
        return renderConfiguration({
          configuration: configurationModelForView(configuration, { hasManagedPassword: managedPasswordPresent }),
          errors: [`测试 SMTP 连接失败：${redacted}`],
          smtpOperations: loadSmtpOperationHistory(paths)
        })
      }
      return reply.code(502).send({ ok: false, error: redacted })
    }
  })

  app.post('/configuration/branding', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const result = validateBranding(request.body)
    if (!result.ok) {
      reply.code(400).type('text/html; charset=utf-8')
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors, values: { branding: result.values } })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors, values: { notifications: result.values } })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: result.errors })
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
      return renderConfiguration({ configuration: configurationModelForView(configuration), errors: ['收件人不存在'] })
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
      const configuration = loadConfiguration(paths)
      const { smtp, secrets } = resolveRuntimeSmtp(paths, configuration, {
        includeResolvedPassword: allowResolvedPassword
      })
      const result = await sendEmailNow({
        paths,
        recipientId: request.body?.recipient_id,
        reportType: request.body?.report_type || 'morning',
        smtp,
        transport: resolvedEmailTransport,
        fetchReport: fetchEmailReport,
        secrets: [...secrets, env.SMTP_PASSWORD]
      })
      return result.ok
        ? reply.code(200).send(result)
        : reply.code(502).send(result)
    } catch (error) {
      if (error.message === '收件人不存在') {
        return reply.code(400).send({ ok: false, error: error.message })
      }
      const managedPassword = hasStoredSmtpPassword(paths) ? safeLoadStoredPassword(paths)?.password : ''
      return reply.code(502).send({ ok: false, error: redactError(error, [managedPassword, env.SMTP_PASSWORD]) })
    }
  })

  app.post('/email/test', async (request, reply) => {
    const configuration = loadConfiguration(paths)
    const recipient = findRecipient(configuration, request.body?.recipient_id)
    const pageMode = isConfigurationPageMode(request.body)
    if (!recipient) {
      appendSmtpOperationHistory(paths, createSmtpOperationRecord({
        action: 'test-email',
        status: 'failed',
        error: '收件人不存在'
      }))
      if (pageMode) {
        reply.code(400).type('text/html; charset=utf-8')
        return renderConfiguration({ configuration: configurationModelForView(configuration), errors: ['收件人不存在'] })
      }
      return reply.code(400).send({ ok: false, error: '收件人不存在' })
    }
    try {
      const { smtp } = resolveRuntimeSmtp(paths, configuration, {
        includeResolvedPassword: allowResolvedPassword
      })
      const senderEmail = configuredSmtpSender(configuration.smtp)
      const delivery = await resolvedEmailTransport.send({
        envelope: {
          from: senderEmail,
          to: recipient.email
        },
        smtp,
        subject: 'Weather Morning Report SMTP test',
        text: 'Weather Morning Report SMTP test message. If you received this, Email delivery is configured.',
        html: '<p>Weather Morning Report SMTP test message.</p><p>If you received this, Email delivery is configured.</p>'
      })
      const messageId = delivery?.messageId || 'smtp-test'
      appendSmtpOperationHistory(paths, createSmtpOperationRecord({
        action: 'test-email',
        status: 'sent',
        recipient,
        messageId
      }))
      if (pageMode) {
        return reply.code(303).header('location', configurationNoticeLocation(`Test Email sent to ${recipient.name}.`)).send()
      }
      return reply.code(200).send({ ok: true, status: 'sent', messageId })
    } catch (error) {
      const managedPasswordPresent = hasStoredSmtpPassword(paths)
      const redacted = redactError(error, [env.SMTP_PASSWORD, ...(managedPasswordPresent ? [safeLoadStoredPassword(paths)?.password].filter(Boolean) : [])])
      appendSmtpOperationHistory(paths, createSmtpOperationRecord({
        action: 'test-email',
        status: 'failed',
        recipient,
        error: redacted
      }))
      if (pageMode) {
        reply.code(502).type('text/html; charset=utf-8')
        return renderConfiguration({
          configuration: configurationModelForView(configuration, { hasManagedPassword: managedPasswordPresent }),
          errors: [`发送测试邮件失败：${redacted}`],
          smtpOperations: loadSmtpOperationHistory(paths)
        })
      }
      return reply.code(502).send({ ok: false, error: redacted })
    }
  })

  app.get('/static/app.css', async (_request, reply) => {
    reply.type('text/css; charset=utf-8')
    return readFileSync(path.join(__dirname, '..', 'static', 'app.css'), 'utf8')
  })

  return app
}

module.exports = { createServiceApp }
