const { existsSync, mkdtempSync, readFileSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const assert = require('node:assert/strict')

const { createServiceApp } = require('../service/app')
const { loadDeliveryHistory } = require('../service/storage/delivery-history-store')
const { loadSmtpOperationHistory } = require('../service/storage/smtp-operation-history-store')
const {
  loadStoredSmtpPassword,
  saveStoredSmtpPassword,
  secretKeyPath,
  secretsPath
} = require('../service/storage/secret-store')
const { loadSchedulerState } = require('../service/scheduler/state-store')

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const createEmailSnapshot = () => ({
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

const createEmailAdvice = () => ({
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

const withTempServiceDirs = async (runner) => {
  const root = mkdtempSync(path.join(tmpdir(), 'wmr-service-'))
  try {
    await runner({
      dataDir: path.join(root, 'data'),
      cacheDir: path.join(root, 'cache'),
      logDir: path.join(root, 'logs')
    })
  } finally {
    rmSync(root, { force: true, recursive: true })
  }
}

test('Fastify service exposes a redacted health endpoint and prepares service directories', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'must-not-leak'
      }
    })

    const response = await app.inject({ method: 'GET', url: '/health' })
    await app.close()

    assert.equal(response.statusCode, 200)
    const body = response.json()
    assert.equal(body.ok, true)
    assert.equal(body.service, 'weather-morning-report')
    assert.equal(body.framework, 'fastify')
    assert.deepEqual(body.directories, { data: true, cache: true, logs: true })
    assert.equal(existsSync(dataDir), true)
    assert.equal(existsSync(cacheDir), true)
    assert.equal(existsSync(logDir), true)
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(dataDir)))
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(cacheDir)))
    assert.doesNotMatch(response.body, new RegExp(escapeRegExp(logDir)))
    assert.doesNotMatch(response.body, /must-not-leak/)
  })
})

test('Fastify service serves the dashboard shell and active CSS', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const dashboard = await app.inject({ method: 'GET', url: '/' })
    const css = await app.inject({ method: 'GET', url: '/static/app.css' })
    await app.close()

    assert.equal(dashboard.statusCode, 200)
    assert.match(dashboard.headers['content-type'], /text\/html/)
    assert.match(dashboard.body, /Weather Morning Report/)
    assert.match(dashboard.body, /href="\/static\/app\.css"/)

    assert.equal(css.statusCode, 200)
    assert.match(css.headers['content-type'], /text\/css/)
    assert.match(css.body, /:root/)
  })
})

test('configuration page creates and renders service-owned default configuration', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.headers['content-type'], /text\/html/)
    assert.match(response.body, /配置中心/)
    assert.match(response.body, /收件人工作台/)
    assert.doesNotMatch(response.body, /\{[%{]/)
    assert.equal(existsSync(path.join(dataDir, 'configuration.json')), true)
  })
})

test('configuration page exposes editable forms for each configuration domain', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(response.statusCode, 200)
    for (const action of [
      '/configuration/defaults',
      '/configuration/recipients',
      '/configuration/schedules',
      '/configuration/smtp',
      '/configuration/branding',
      '/configuration/notifications'
    ]) {
      assert.match(response.body, new RegExp(`action="${escapeRegExp(action)}"`))
    }
    assert.match(response.body, /name="local_send_time"/)
    assert.match(response.body, /name="accent_color"/)
    assert.match(response.body, /name="retention_days"/)
  })
})

test('logs page renders an empty state when the log file is missing', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({ method: 'GET', url: '/logs' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /暂无服务日志/)
  })
})

test('dashboard links to configuration logs and active CSS', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({ method: 'GET', url: '/' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /href="\/configuration"/)
    assert.match(response.body, /href="\/logs"/)
    assert.match(response.body, /href="\/scheduler"/)
    assert.match(response.body, /href="\/static\/app\.css"/)
  })
})

test('configuration page escapes user-controlled values', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=%3Cscript%3Ealert(1)%3C%2Fscript%3E&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const response = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.doesNotMatch(response.body, /<script>alert/)
    assert.match(response.body, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
  })
})

test('recipient form rejects invalid email and preserves safe form values', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=not-an-email&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /邮箱格式无效/)
    assert.match(response.body, /value="Mango"/)
  })
})

test('recipient form accepts a valid recipient and persists it', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(response.headers.location, '/configuration')
    assert.equal(configuration.recipients.length, 1)
    assert.equal(configuration.recipients[0].email, 'mango@example.com')
  })
})

test('schedule form rejects unknown recipient ids', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/schedules',
      payload: 'recipient_id=missing&local_send_time=08%3A30&report_type=morning&send_policy=always&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /收件人不存在/)
  })
})

test('schedule form rejects impossible local times', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/schedules',
      payload: 'recipient_id=recipient-1&local_send_time=99%3A99&report_type=morning&send_policy=always&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /发送时间必须是 HH:MM 格式/)
  })
})

test('smtp form never echoes submitted password', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const page = await app.inject({ method: 'GET', url: '/configuration' })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.smtp.passwordSaved, true)
    assert.doesNotMatch(JSON.stringify(configuration), /super-secret/)
    assert.doesNotMatch(page.body, /super-secret/)
    assert.match(page.body, /已保存，留空保持不变/)
  })
})

test('smtp form stores passwords in managed secret storage instead of configuration json', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    const stored = loadStoredSmtpPassword({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.smtp.passwordSaved, true)
    assert.doesNotMatch(JSON.stringify(configuration), /super-secret/)
    assert.equal(stored.password, 'super-secret')
  })
})

test('smtp transport prefers managed smtp password over runtime env fallback', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const sentMessages = []
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'env-secret'
      },
      createEmailTransport: ({ env }) => {
        assert.equal(env.SMTP_PASSWORD, 'env-secret')
        return {
          async send (message) {
            sentMessages.push(message)
            return { messageId: 'smtp-route-message-1' }
          }
        }
      },
      fetchEmailReport: async () => ({
        snapshot: createEmailSnapshot(),
        advice: createEmailAdvice(),
        cached: false
      })
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=managed-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/send-now',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(response.json().messageId, 'smtp-route-message-1')
    assert.equal(sentMessages.length, 1)
    assert.equal(sentMessages[0].smtp.resolvedPassword, 'managed-secret')
  })
})

test('smtp clear-password route removes managed secret and resets password saved state', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/clear-password',
      payload: 'page_mode=configuration',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    const stored = loadStoredSmtpPassword({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.smtp.passwordSaved, false)
    assert.equal(stored, null)
  })
})

test('configuration page renders secret health backup warning without leaking secret material', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /密钥与备份状态/)
    assert.match(page.body, /本地密钥尚未确认备份/)
    assert.match(page.body, /action="\/configuration\/secrets\/confirm-backup"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('secret backup confirmation routes toggle notification metadata', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    const confirmed = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    let configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    assert.equal(confirmed.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, true)

    const revoked = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/revoke-backup-confirmation',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(revoked.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, false)
  })
})

test('configuration page renders healthy secret backup state after confirmation', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.match(page.body, /本地密钥已确认备份/)
    assert.match(page.body, /action="\/configuration\/secrets\/revoke-backup-confirmation"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('configuration page renders degraded secret health without failing', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const paths = { dataDir, cacheDir, logDir }
    saveStoredSmtpPassword(paths, 'super-secret-password')
    require('node:fs').writeFileSync(secretKeyPath(paths), 'not-valid-base64')
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /本地密钥缺失或无效/)
    assert.doesNotMatch(page.body, /super-secret-password|not-valid-base64/)
  })
})

test('smtp form can replace corrupt managed secret storage after health warning', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const paths = { dataDir, cacheDir, logDir }
    require('node:fs').mkdirSync(dataDir, { recursive: true })
    require('node:fs').writeFileSync(secretsPath(paths), '{"smtpPassword":')
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    const degradedPage = await app.inject({ method: 'GET', url: '/configuration' })
    assert.equal(degradedPage.statusCode, 200)
    assert.match(degradedPage.body, /已保存的 SMTP 密码无法解密/)

    const saved = await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=recovered-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(saved.statusCode, 303)
    assert.equal(loadStoredSmtpPassword(paths).password, 'recovered-secret')
  })
})

test('configuration page renders a key rotation action for healthy managed secret state', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /密钥与备份状态/)
    assert.match(page.body, /action="\/configuration\/secrets\/rotate-key"/)
    assert.doesNotMatch(page.body, /super-secret/)
  })
})

test('secret key rotation route rotates the key and resets backup confirmation', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/rotate-key',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const configuration = JSON.parse(readFileSync(path.join(dataDir, 'configuration.json'), 'utf8'))
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.equal(configuration.notifications.secretKeyBackupConfirmed, false)
    assert.match(response.headers.location || '', /^\/configuration\?smtp_notice=/)
  })
})

test('secret key rotation route fails safely when managed secret is not decryptable', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    require('node:fs').writeFileSync(secretsPath({ dataDir, cacheDir, logDir }), '{"smtpPassword":')

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/secrets/rotate-key',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.match(response.body, /已保存的 SMTP 密码无法解密|stored SMTP password could not be decrypted/)
    assert.doesNotMatch(response.body, /super-secret/)
  })
})

test('secret key rotation route rolls back when configuration persistence fails', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const setupApp = createServiceApp({
      env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
    })

    await setupApp.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=super-secret&security=starttls&sender_email=mango%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await setupApp.inject({
      method: 'POST',
      url: '/configuration/secrets/confirm-backup',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await setupApp.close()

    const appModulePath = require.resolve('../service/app')
    const configurationStoreModulePath = require.resolve('../service/storage/configuration-store')
    delete require.cache[appModulePath]
    delete require.cache[configurationStoreModulePath]

    let saveCalls = 0
    const configurationFile = path.join(dataDir, 'configuration.json')
    const originalWriteFileSync = require('node:fs').writeFileSync
    const beforeKey = readFileSync(secretKeyPath({ dataDir, cacheDir, logDir }), 'utf8')
    const beforeSecret = loadStoredSmtpPassword({ dataDir, cacheDir, logDir })
    try {
      require('node:fs').writeFileSync = (...args) => {
        if (String(args[0]) === configurationFile) {
          saveCalls += 1
          if (saveCalls >= 2) {
            throw new Error('simulated configuration persistence failure')
          }
        }
        return originalWriteFileSync(...args)
      }

      const { createServiceApp: createFreshServiceApp } = require('../service/app')
      const app = createFreshServiceApp({
        env: { OPENPET_DATA_DIR: dataDir, OPENPET_CACHE_DIR: cacheDir, OPENPET_LOG_DIR: logDir }
      })

      const response = await app.inject({
        method: 'POST',
        url: '/configuration/secrets/rotate-key',
        payload: '',
        headers: { 'content-type': 'application/x-www-form-urlencoded' }
      })

      const afterKey = readFileSync(secretKeyPath({ dataDir, cacheDir, logDir }), 'utf8')
      const afterSecret = loadStoredSmtpPassword({ dataDir, cacheDir, logDir })
      const configuration = JSON.parse(readFileSync(configurationFile, 'utf8'))
      await app.close()

      assert.equal(response.statusCode, 502)
      assert.match(response.body, /rotation failed/)
      assert.equal(afterKey, beforeKey)
      assert.equal(afterSecret.password, beforeSecret.password)
      assert.equal(configuration.notifications.secretKeyBackupConfirmed, true)
    } finally {
      require('node:fs').writeFileSync = originalWriteFileSync
      delete require.cache[appModulePath]
      delete require.cache[configurationStoreModulePath]
    }
  })
})

test('configuration page renders SMTP operational controls', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /action="\/configuration\/smtp\/test-connection"/)
    assert.match(page.body, /action="\/email\/test"/)
    assert.match(page.body, /value="recipient-1"/)
  })
})

test('configuration page can render SMTP operation success notices', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration?smtp_notice=SMTP%20connection%20verified' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /SMTP connection verified/)
    assert.match(page.body, /notice-success/)
    assert.match(page.body, /action="\/configuration\/smtp\/test-connection"/)
  })
})

test('configuration page renders recent SMTP operational history', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration?smtp_notice=recent-history-placeholder' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /recent-history-placeholder/)
    assert.match(page.body, /SMTP operational history/)
    assert.match(page.body, /test-connection · connected/)
  })
})

test('configuration page filters SMTP operational history and preserves selected filters', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        },
        async send () {
          return { messageId: 'smtp-test-message-1' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const page = await app.inject({ method: 'GET', url: '/configuration?smtp_action=test-email&smtp_status=sent&smtp_recipient_id=recipient-1' })
    await app.close()

    assert.equal(page.statusCode, 200)
    assert.match(page.body, /name="smtp_action"/)
    assert.match(page.body, /option value="test-email" selected/)
    assert.match(page.body, /option value="sent" selected/)
    assert.match(page.body, /option value="recipient-1" selected/)
    assert.match(page.body, /test-email · sent/)
    assert.doesNotMatch(page.body, /test-connection · connected/)
  })
})

test('SMTP operational history JSON export honors active filters', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        },
        async send () {
          return { messageId: 'smtp-test-message-1' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'GET',
      url: '/configuration/smtp/history/export?format=json&smtp_action=test-email&smtp_status=sent&smtp_recipient_id=recipient-1'
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.headers['content-type'], /application\/json/)
    assert.equal(response.json().ok, true)
    assert.deepEqual(response.json().filters, {
      action: 'test-email',
      status: 'sent',
      recipientId: 'recipient-1'
    })
    assert.deepEqual(response.json().records.map((record) => record.action), ['test-email'])
    assert.deepEqual(response.json().records.map((record) => record.status), ['sent'])
  })
})

test('SMTP operational history CSV export honors active filters and downloads as attachment', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        },
        async send () {
          return { messageId: 'smtp-test-message-1' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'GET',
      url: '/configuration/smtp/history/export?format=csv&smtp_action=test-email&smtp_status=sent&smtp_recipient_id=recipient-1'
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.headers['content-type'], /text\/csv/)
    assert.match(response.headers['content-disposition'] || '', /attachment;/)
    assert.match(response.body, /^id,createdAt,action,status,recipientId,recipientName,recipientEmail,messageId,error\n/)
    assert.match(response.body, /test-email/)
    assert.doesNotMatch(response.body, /test-connection/)
    assert.match(response.body, /\n$/)
  })
})

test('SMTP operational history export rejects unsupported formats', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'GET',
      url: '/configuration/smtp/history/export?format=xml'
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.deepEqual(response.json(), { ok: false, error: 'Unsupported SMTP history export format' })
  })
})

test('smtp test connection route verifies current configuration without sending email', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const calls = []
    const transport = {
      async verify (message) {
        calls.push(message)
        return { ok: true }
      },
      async send () {
        throw new Error('test connection must not send email')
      }
    }
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'runtime-secret'
      },
      emailTransport: transport
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.deepEqual(response.json(), { ok: true, status: 'connected' })
    assert.equal(calls.length, 1)
    assert.equal(calls[0].smtp.host, 'smtp.example.com')
    assert.equal(calls[0].smtp.passwordSaved, true)
    assert.doesNotMatch(JSON.stringify(calls), /runtime-secret/)
  })
})

test('smtp test connection route appends operational history on success', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(history.length, 1)
    assert.equal(history[0].action, 'test-connection')
    assert.equal(history[0].status, 'connected')
  })
})

test('page-mode smtp test connection redirects to configuration with success notice', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          return { ok: true }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: 'page_mode=configuration',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.match(response.headers.location || '', /^\/configuration\?smtp_notice=/)
  })
})

test('smtp test connection route appends redacted operational history on failure', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'runtime-secret'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      emailTransport: {
        async verify () {
          throw new Error(`SMTP auth failed for ${secret}`)
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(history.length, 1)
    assert.equal(history[0].action, 'test-connection')
    assert.equal(history[0].status, 'failed')
    assert.match(history[0].error, /\[redacted\]/)
    assert.doesNotMatch(JSON.stringify(history), new RegExp(secret))
  })
})

test('smtp test connection route redacts transport failures', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'runtime-secret'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      emailTransport: {
        async verify () {
          throw new Error(`SMTP auth failed for ${secret}`)
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /\[redacted\]/)
    assert.doesNotMatch(response.body, new RegExp(secret))
  })
})

test('smtp test connection route fails safely when managed secret storage is corrupted', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'env-secret'
      },
      emailTransport: {
        async verify () {
          throw new Error('verify should not run with corrupted managed secret')
        }
      }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=managed-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const secrets = JSON.parse(readFileSync(secretsPath({ dataDir, cacheDir, logDir }), 'utf8'))
    secrets.smtpPassword.ciphertext = 'not-valid-base64'
    require('node:fs').writeFileSync(secretsPath({ dataDir, cacheDir, logDir }), `${JSON.stringify(secrets, null, 2)}\n`)

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /stored SMTP password could not be decrypted/)
    assert.equal(history.at(-1)?.status, 'failed')
    assert.match(history.at(-1)?.error || '', /stored SMTP password could not be decrypted/)
    assert.doesNotMatch(response.body, /managed-secret|env-secret/)
  })
})

test('smtp test connection route fails safely when managed secret file is unreadable', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const paths = { dataDir, cacheDir, logDir }
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'env-secret'
      },
      emailTransport: {
        async verify () {
          throw new Error('verify should not run with unreadable managed secret storage')
        }
      }
    })

    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=managed-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    require('node:fs').writeFileSync(secretsPath(paths), '{"smtpPassword":')

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory(paths)
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /stored SMTP password could not be decrypted/)
    assert.equal(history.at(-1)?.status, 'failed')
    assert.match(history.at(-1)?.error || '', /stored SMTP password could not be decrypted/)
    assert.doesNotMatch(response.body, /managed-secret|env-secret|smtpPassword/)
  })
})

test('page-mode smtp test connection failure re-renders configuration with redacted warning', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'runtime-secret'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      emailTransport: {
        async verify () {
          throw new Error(`SMTP auth failed for ${secret}`)
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: 'page_mode=configuration',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.match(response.headers['content-type'], /text\/html/)
    assert.match(response.body, /\[redacted\]/)
    assert.doesNotMatch(response.body, new RegExp(secret))
    assert.match(response.body, /测试 SMTP 连接/)
  })
})

test('smtp test connection route rejects missing configured sender before transport verify', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    let verifyCalls = 0
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async verify () {
          verifyCalls += 1
          return { ok: true }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=&password=&security=starttls&sender_email=',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/smtp/test-connection',
      payload: '',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /SMTP sender email is required/)
    assert.equal(verifyCalls, 0)
  })
})

test('branding form rejects invalid accent color', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/branding',
      payload: 'report_title=Weather&accent_color=blue&footer_text=Footer&greeting_visible=on&data_source_visible=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /强调色必须是 #RRGGBB 格式/)
  })
})

test('manual preview renders confirmation without sending email', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/manual/preview',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /手动发送预览/)
    assert.match(response.body, /确认并加入发送队列/)
    assert.doesNotMatch(response.body, /Email sent|SMTP|已发送/)
  })
})

test('email preview route renders HTML without sending email', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const transport = {
      sentMessages: [],
      async send (message) {
        this.sentMessages.push(message)
        return { messageId: 'unexpected' }
      }
    }
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: transport,
      fetchEmailReport: async () => ({
        snapshot: createEmailSnapshot(),
        advice: createEmailAdvice(),
        cached: false
      })
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=3&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({ method: 'GET', url: '/email/preview?recipient_id=recipient-1&report_type=morning' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.headers['content-type'], /text\/html/)
    assert.match(response.body, /邮件预览/)
    assert.match(response.body, /<iframe sandbox=""/)
    assert.match(response.body, /data-email-template=&quot;3&quot;/)
    assert.equal(transport.sentMessages.length, 0)
  })
})

test('email preview route redacts unexpected report errors', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'must-not-leak-preview'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      fetchEmailReport: async () => {
        throw new Error(`Preview failed with ${secret}`)
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=3&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({ method: 'GET', url: '/email/preview?recipient_id=recipient-1&report_type=morning' })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /\[redacted\]/)
    assert.doesNotMatch(response.body, new RegExp(secret))
  })
})

test('email send-now route sends through injected transport and records history', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const transport = {
      sentMessages: [],
      async send (message) {
        this.sentMessages.push(message)
        return { messageId: 'route-message-1' }
      }
    }
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'must-not-leak'
      },
      emailTransport: transport,
      fetchEmailReport: async () => ({
        snapshot: createEmailSnapshot(),
        advice: createEmailAdvice(),
        cached: false
      })
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/send-now',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadDeliveryHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(response.json().status, 'sent')
    assert.equal(response.json().messageId, 'route-message-1')
    assert.equal(transport.sentMessages.length, 1)
    assert.match(transport.sentMessages[0].html, /data-email-template="5"/)
    assert.equal(history.length, 1)
    assert.equal(history[0].status, 'sent')
    assert.doesNotMatch(JSON.stringify(history), /must-not-leak|<html/i)
  })
})

test('email send-now route uses SMTP transport factory by default', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const sentMessages = []
    let factoryCalls = 0
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'runtime-secret'
      },
      createEmailTransport: ({ env }) => {
        factoryCalls += 1
        assert.equal(env.SMTP_PASSWORD, 'runtime-secret')
        return {
          async send (message) {
            sentMessages.push(message)
            return { messageId: 'smtp-route-message-1' }
          }
        }
      },
      fetchEmailReport: async () => ({
        snapshot: createEmailSnapshot(),
        advice: createEmailAdvice(),
        cached: false
      })
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/send-now',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(response.json().messageId, 'smtp-route-message-1')
    assert.equal(factoryCalls, 1)
    assert.equal(sentMessages.length, 1)
    assert.equal(sentMessages[0].smtp.host, 'smtp.example.com')
    assert.equal(sentMessages[0].smtp.username, 'mango')
    assert.equal(sentMessages[0].smtp.passwordSaved, true)
    assert.doesNotMatch(JSON.stringify(sentMessages), /runtime-secret/)
  })
})

test('email test route sends operational test message without delivery history', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const sentMessages = []
    const transport = {
      async send (message) {
        sentMessages.push(message)
        return { messageId: 'smtp-test-message-1' }
      }
    }
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: 'runtime-secret'
      },
      emailTransport: transport
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadDeliveryHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.deepEqual(response.json(), { ok: true, status: 'sent', messageId: 'smtp-test-message-1' })
    assert.equal(sentMessages.length, 1)
    assert.equal(sentMessages[0].envelope.from, 'sender@example.com')
    assert.equal(sentMessages[0].envelope.to, 'mango@example.com')
    assert.equal(sentMessages[0].smtp.host, 'smtp.example.com')
    assert.match(sentMessages[0].subject, /SMTP test/)
    assert.match(sentMessages[0].text, /Weather Morning Report SMTP test/)
    assert.deepEqual(history, [])
    assert.doesNotMatch(JSON.stringify(sentMessages), /runtime-secret/)
  })
})

test('email test route appends operational history on success', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async send () {
          return { messageId: 'smtp-test-message-1' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(history.length, 1)
    assert.equal(history[0].action, 'test-email')
    assert.equal(history[0].status, 'sent')
    assert.equal(history[0].recipientEmail, 'mango@example.com')
  })
})

test('page-mode email test redirects to configuration with recipient success notice', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async send () {
          return { messageId: 'smtp-test-message-1' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1&page_mode=configuration',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 303)
    assert.match(response.headers.location || '', /^\/configuration\?smtp_notice=/)
    assert.match(decodeURIComponent(response.headers.location || ''), /Mango/)
  })
})

test('email test route appends redacted operational history on failure', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'runtime-secret'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      emailTransport: {
        async send () {
          throw new Error(`SMTP send failed with ${secret}`)
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(history.length, 1)
    assert.equal(history[0].action, 'test-email')
    assert.equal(history[0].status, 'failed')
    assert.match(history[0].error, /\[redacted\]/)
    assert.doesNotMatch(JSON.stringify(history), new RegExp(secret))
  })
})

test('email test route appends operational history for missing recipients', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=missing',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    const history = loadSmtpOperationHistory({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.equal(history.length, 1)
    assert.equal(history[0].action, 'test-email')
    assert.equal(history[0].status, 'failed')
    assert.match(history[0].error, /收件人不存在/)
  })
})

test('page-mode email test failure re-renders configuration with redacted warning', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'runtime-secret'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      emailTransport: {
        async send () {
          throw new Error(`SMTP send failed with ${secret}`)
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=mango&password=runtime-secret&security=starttls&sender_email=sender%40example.com',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1&page_mode=configuration',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.match(response.headers['content-type'], /text\/html/)
    assert.match(response.body, /\[redacted\]/)
    assert.doesNotMatch(response.body, new RegExp(secret))
    assert.match(response.body, /发送测试邮件/)
  })
})

test('email test route rejects missing configured sender before transport send', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    let sendCalls = 0
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      emailTransport: {
        async send () {
          sendCalls += 1
          return { messageId: 'unexpected' }
        }
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/smtp',
      payload: 'host=smtp.example.com&port=587&username=&password=&security=starttls&sender_email=',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/test',
      payload: 'recipient_id=recipient-1',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /SMTP sender email is required/)
    assert.equal(sendCalls, 0)
  })
})

test('email send-now route rejects unknown recipients safely', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      fetchEmailReport: async () => ({
        snapshot: createEmailSnapshot(),
        advice: createEmailAdvice(),
        cached: false
      })
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/send-now',
      payload: 'recipient_id=missing&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /收件人不存在/)
  })
})

test('email send-now route redacts unexpected report errors', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const secret = 'must-not-leak'
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir,
        SMTP_PASSWORD: secret
      },
      fetchEmailReport: async () => {
        throw new Error(`Report generation failed with ${secret}`)
      }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Mango&email=mango%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=5&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/email/send-now',
      payload: 'recipient_id=recipient-1&report_type=morning',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 502)
    assert.equal(response.json().ok, false)
    assert.match(response.json().error, /\[redacted\]/)
    assert.doesNotMatch(response.body, new RegExp(secret))
  })
})

test('scheduler page renders queue and worker status', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({ method: 'GET', url: '/scheduler' })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.match(response.body, /调度队列/)
    assert.match(response.body, /Pending/)
    assert.match(response.body, /Worker inactive/)
  })
})

test('scheduler enqueue-due route creates due automatic jobs', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      },
      schedulerNow: () => new Date('2026-06-08T00:30:00.000Z')
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/recipients',
      payload: 'name=Alice&email=alice%40example.com&location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&email_template=1&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.inject({
      method: 'POST',
      url: '/configuration/schedules',
      payload: 'recipient_id=recipient-1&local_send_time=08%3A30&report_type=morning&send_policy=always&enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })

    const response = await app.inject({ method: 'POST', url: '/scheduler/enqueue-due' })
    const duplicate = await app.inject({ method: 'POST', url: '/scheduler/enqueue-due' })
    const state = loadSchedulerState({ dataDir, cacheDir, logDir })
    await app.close()

    assert.equal(response.statusCode, 200)
    assert.equal(response.json().created, 1)
    assert.equal(duplicate.json().created, 0)
    assert.equal(state.jobs.length, 1)
    assert.equal(state.jobs[0].dedupeKey, 'automatic:recipient-1:schedule-1:morning:2026-06-08')
  })
})

test('defaults form rejects invalid report type', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/defaults',
      payload: 'location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&local_send_time=08%3A30&report_type=night&send_policy=always&schedule_enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /报告类型无效/)
  })
})

test('defaults form rejects impossible local times', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/defaults',
      payload: 'location_name=Shanghai&location_query=Shanghai&timezone=Asia%2FShanghai&language=zh-CN&local_send_time=24%3A00&report_type=morning&send_policy=always&schedule_enabled=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /默认发送时间必须是 HH:MM 格式/)
  })
})

test('notifications form rejects negative retention days', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/notifications',
      payload: 'admin_email=admin%40example.com&webhook_url=&retention_days=-1&alert_cooldown_minutes=60&webhook_enabled=on&secret_key_backup_confirmed=on',
      headers: { 'content-type': 'application/x-www-form-urlencoded' }
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /历史保留天数必须是非负整数/)
  })
})

test('empty form submissions return validation errors instead of server errors', async () => {
  await withTempServiceDirs(async ({ dataDir, cacheDir, logDir }) => {
    const app = createServiceApp({
      env: {
        OPENPET_DATA_DIR: dataDir,
        OPENPET_CACHE_DIR: cacheDir,
        OPENPET_LOG_DIR: logDir
      }
    })

    const response = await app.inject({
      method: 'POST',
      url: '/configuration/notifications'
    })
    await app.close()

    assert.equal(response.statusCode, 400)
    assert.match(response.body, /历史保留天数必须是非负整数/)
  })
})
