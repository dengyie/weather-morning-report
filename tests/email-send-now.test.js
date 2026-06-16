const { existsSync, mkdtempSync, readFileSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const assert = require('node:assert/strict')

const { createDefaultConfiguration } = require('../service/configuration/defaults')
const { saveConfiguration } = require('../service/storage/configuration-store')
const { appendDeliveryHistory, deliveryHistoryPath, loadDeliveryHistory } = require('../service/storage/delivery-history-store')
const { sendEmailNow } = require('../service/email/send-now')
const { createFakeEmailTransport } = require('../service/email/transports')

const withTempServiceDirs = async (runner) => {
  const root = mkdtempSync(path.join(tmpdir(), 'wmr-email-'))
  try {
    const paths = {
      dataDir: path.join(root, 'data'),
      cacheDir: path.join(root, 'cache'),
      logDir: path.join(root, 'logs')
    }
    await runner(paths)
  } finally {
    rmSync(root, { force: true, recursive: true })
  }
}

const createSnapshot = () => ({
  schemaVersion: 1,
  location: { name: 'Shanghai', query: 'Shanghai' },
  source: { host: 'wttr.in', url: 'https://wttr.in/Shanghai?format=j1' },
  fetchedAt: '2026-06-17T08:00:00.000Z',
  current: {
    condition: 'Clear',
    description: 'Sunny',
    temperatureC: 31,
    feelsLikeC: 35,
    humidityPercent: 72,
    windSpeedKph: 12,
    uvIndex: 8
  },
  daily: {
    date: '2026-06-17',
    minimumTemperatureC: 25,
    maximumTemperatureC: 34,
    uvIndex: 8
  },
  hourly: []
})

const createAdvice = () => ({
  schemaVersion: 1,
  subject: '[紫外线很强，注意防晒] 天气早报',
  focus: '午间紫外线较强',
  umbrella: '今天通常不用带伞',
  sunscreen: 'UV 8，强烈建议防晒、遮阳，长时间户外注意补涂',
  clothing: '短袖或透气薄上衣搭配轻薄下装，注意通风散热',
  closing: '午间阳光强，出门记得做好防晒。',
  periods: [
    { label: '早通勤', summary: '晴，降雨概率最高 0% ，体感约 29°C' },
    { label: '午间', summary: '晴，降雨概率最高 0% ，体感约 35°C' }
  ],
  signals: {
    highestRiskLevel: 0,
    umbrellaLevel: 0,
    sunscreenLevel: 3,
    clothingLevel: 3,
    targetPrecipitationLevel: 0,
    thunderstorm: false,
    strongWind: false,
    dangerousHeat: false
  }
})

const seedConfiguration = (paths) => {
  const configuration = createDefaultConfiguration()
  configuration.smtp = {
    ...configuration.smtp,
    senderEmail: 'sender@example.com',
    passwordSaved: true
  }
  configuration.recipients = [{
    id: 'recipient-1',
    name: 'Mango',
    email: 'mango@example.com',
    locationName: 'Shanghai',
    locationQuery: 'Shanghai',
    timezone: 'Asia/Shanghai',
    language: 'zh-CN',
    emailTemplate: '2',
    enabled: true
  }]
  saveConfiguration(paths, configuration)
  return configuration
}

const fetchReport = async () => ({
  snapshot: createSnapshot(),
  advice: createAdvice(),
  cached: false
})

test('delivery history storage creates bounded newest-last records', async () => {
  await withTempServiceDirs(async (paths) => {
    assert.deepEqual(loadDeliveryHistory(paths), [])
    appendDeliveryHistory(paths, { id: 'delivery-1', status: 'sent' }, { limit: 2 })
    appendDeliveryHistory(paths, { id: 'delivery-2', status: 'failed' }, { limit: 2 })
    appendDeliveryHistory(paths, { id: 'delivery-3', status: 'sent' }, { limit: 2 })

    assert.equal(existsSync(deliveryHistoryPath(paths)), true)
    assert.deepEqual(loadDeliveryHistory(paths).map((record) => record.id), ['delivery-2', 'delivery-3'])
    assert.match(readFileSync(deliveryHistoryPath(paths), 'utf8'), /\n$/)
  })
})

test('sendEmailNow sends through fake transport and records redacted sent history', async () => {
  await withTempServiceDirs(async (paths) => {
    seedConfiguration(paths)
    const transport = createFakeEmailTransport({ messageId: 'fake-message-1' })
    const result = await sendEmailNow({
      paths,
      recipientId: 'recipient-1',
      reportType: 'morning',
      transport,
      now: () => new Date('2026-06-17T08:30:00.000Z'),
      fetchReport
    })

    assert.equal(result.ok, true)
    assert.equal(result.status, 'sent')
    assert.equal(result.messageId, 'fake-message-1')
    assert.equal(transport.sentMessages.length, 1)
    assert.equal(transport.sentMessages[0].envelope.to, 'mango@example.com')
    assert.match(transport.sentMessages[0].html, /data-email-template="2"/)

    const history = loadDeliveryHistory(paths)
    assert.equal(history.length, 1)
    assert.equal(history[0].status, 'sent')
    assert.equal(history[0].recipientEmail, 'mango@example.com')
    assert.equal(history[0].templateId, '2')
    assert.equal(history[0].templateLabel, '行动风格')
    assert.equal(history[0].messageId, 'fake-message-1')
    assert.doesNotMatch(JSON.stringify(history), /<html|super-secret|password/i)
  })
})

test('sendEmailNow records failed transport errors without leaking secrets', async () => {
  await withTempServiceDirs(async (paths) => {
    seedConfiguration(paths)
    const secret = 'super-secret-password'
    const transport = {
      async send () {
        throw new Error(`SMTP login failed for ${secret}`)
      }
    }

    const result = await sendEmailNow({
      paths,
      recipientId: 'recipient-1',
      reportType: 'morning',
      transport,
      now: () => new Date('2026-06-17T08:30:00.000Z'),
      fetchReport,
      secrets: [secret]
    })

    assert.equal(result.ok, false)
    assert.equal(result.status, 'failed')
    assert.match(result.error, /\[redacted\]/)
    assert.doesNotMatch(result.error, new RegExp(secret))

    const history = loadDeliveryHistory(paths)
    assert.equal(history.length, 1)
    assert.equal(history[0].status, 'failed')
    assert.match(history[0].error, /\[redacted\]/)
    assert.doesNotMatch(JSON.stringify(history), new RegExp(secret))
  })
})

test('sendEmailNow records failed report generation errors without leaking secrets', async () => {
  await withTempServiceDirs(async (paths) => {
    seedConfiguration(paths)
    const secret = 'super-secret-report-token'
    const transport = createFakeEmailTransport()

    const result = await sendEmailNow({
      paths,
      recipientId: 'recipient-1',
      reportType: 'morning',
      transport,
      now: () => new Date('2026-06-17T08:30:00.000Z'),
      fetchReport: async () => {
        throw new Error(`Report token ${secret} rejected`)
      },
      secrets: [secret]
    })

    assert.equal(result.ok, false)
    assert.equal(result.status, 'failed')
    assert.match(result.error, /\[redacted\]/)
    assert.equal(transport.sentMessages.length, 0)

    const history = loadDeliveryHistory(paths)
    assert.equal(history.length, 1)
    assert.equal(history[0].status, 'failed')
    assert.equal(history[0].templateId, '2')
    assert.match(history[0].error, /\[redacted\]/)
    assert.doesNotMatch(JSON.stringify(history), new RegExp(secret))
  })
})

test('sendEmailNow rejects missing recipients before transport send', async () => {
  await withTempServiceDirs(async (paths) => {
    seedConfiguration(paths)
    const transport = createFakeEmailTransport()
    await assert.rejects(
      sendEmailNow({
        paths,
        recipientId: 'missing',
        reportType: 'morning',
        transport,
        fetchReport
      }),
      /收件人不存在/
    )
    assert.equal(transport.sentMessages.length, 0)
    assert.deepEqual(loadDeliveryHistory(paths), [])
  })
})
