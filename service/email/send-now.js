const { renderEmailReport } = require('../../rendering/email-renderer')
const { emailTemplateLabel, normalizeEmailTemplate } = require('../../rendering/email-template-options')
const { recommendWeather } = require('../../core/recommendation-engine')
const { loadConfiguration } = require('../storage/configuration-store')
const { appendDeliveryHistory } = require('../storage/delivery-history-store')

let deliverySequence = 0

const redactError = (error, secrets = []) => {
  let message = error?.message || String(error || 'Email delivery failed')
  for (const secret of secrets.filter(Boolean)) {
    message = message.split(String(secret)).join('[redacted]')
  }
  return message.replace(/password=[^\s&]+/gi, 'password=[redacted]')
}

const createDeliveryId = (now) => {
  deliverySequence += 1
  return `delivery-${now.toISOString().replace(/[:.]/g, '-')}-${deliverySequence}`
}

const findRecipient = (configuration, recipientId) => configuration.recipients
  .find((recipient) => recipient.id === recipientId && !recipient.archivedAt)

const defaultFetchReport = async ({ recipient, reportType }) => {
  const fetchedAt = new Date().toISOString()
  const snapshot = {
    schemaVersion: 1,
    location: {
      name: recipient.locationName,
      query: recipient.locationQuery
    },
    source: {
      host: 'local-preview',
      url: ''
    },
    fetchedAt,
    current: {
      condition: 'Unknown',
      description: 'Preview data unavailable',
      temperatureC: null,
      feelsLikeC: null,
      humidityPercent: null,
      windSpeedKph: null,
      uvIndex: null
    },
    daily: {
      date: fetchedAt.slice(0, 10),
      minimumTemperatureC: null,
      maximumTemperatureC: null,
      uvIndex: null
    },
    hourly: []
  }
  return {
    snapshot,
    advice: recommendWeather(snapshot, {
      language: recipient.language,
      reportType
    }),
    cached: true
  }
}

const buildHistoryRecord = ({ id, createdAt, recipient, reportType, rendered, status, messageId, error }) => ({
  id,
  createdAt: createdAt.toISOString(),
  recipientId: recipient.id,
  recipientEmail: recipient.email,
  reportType,
  templateId: rendered.templateId,
  templateLabel: rendered.templateLabel,
  status,
  ...(messageId ? { messageId } : {}),
  ...(error ? { error } : {})
})

const fallbackRenderedMetadata = (recipient) => {
  const templateId = normalizeEmailTemplate(recipient.emailTemplate)
  return {
    templateId,
    templateLabel: emailTemplateLabel(templateId)
  }
}

const sendEmailNow = async ({
  paths,
  recipientId,
  reportType = 'morning',
  transport,
  now = () => new Date(),
  fetchReport = defaultFetchReport,
  secrets = []
}) => {
  const configuration = loadConfiguration(paths)
  const recipient = findRecipient(configuration, recipientId)
  if (!recipient) {
    throw new Error('收件人不存在')
  }
  const createdAt = now()
  const id = createDeliveryId(createdAt)
  const senderEmail = configuration.smtp.senderEmail || configuration.smtp.username || 'weather-morning-report@localhost'
  let rendered = fallbackRenderedMetadata(recipient)

  try {
    const report = await fetchReport({ recipient, reportType, configuration })
    rendered = renderEmailReport({
      snapshot: report.snapshot,
      advice: report.advice,
      recipient,
      branding: configuration.branding,
      reportType,
      cached: report.cached
    })
    const delivery = await transport.send({
      envelope: {
        from: senderEmail,
        to: recipient.email
      },
      smtp: configuration.smtp,
      subject: rendered.subject,
      text: rendered.text,
      html: rendered.html
    })
    const messageId = delivery?.messageId || id
    const record = buildHistoryRecord({ id, createdAt, recipient, reportType, rendered, status: 'sent', messageId })
    appendDeliveryHistory(paths, record)
    return { ok: true, status: 'sent', id, messageId, templateId: rendered.templateId, templateLabel: rendered.templateLabel }
  } catch (error) {
    const redacted = redactError(error, secrets)
    const record = buildHistoryRecord({ id, createdAt, recipient, reportType, rendered, status: 'failed', error: redacted })
    appendDeliveryHistory(paths, record)
    return { ok: false, status: 'failed', id, error: redacted, templateId: rendered.templateId, templateLabel: rendered.templateLabel }
  }
}

module.exports = { defaultFetchReport, redactError, sendEmailNow }
