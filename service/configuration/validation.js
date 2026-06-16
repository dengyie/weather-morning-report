const { LANGUAGES, REPORT_TYPES, SEND_POLICIES, SMTP_SECURITY_MODES } = require('./defaults')

const normalizeBoolean = (value) => value === 'on' || value === 'true' || value === '1' || value === true
const trim = (value) => String(value || '').trim()
const isValidLocalTime = (value) => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)

const hasSingleAt = (value) => {
  const parts = value.split('@')
  return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0
}

const validateRecipient = (payload = {}) => {
  const values = {
    id: trim(payload.recipient_id),
    name: trim(payload.name),
    email: trim(payload.email),
    locationName: trim(payload.location_name),
    locationQuery: trim(payload.location_query),
    timezone: trim(payload.timezone),
    language: trim(payload.language) || 'zh-CN',
    emailTemplate: trim(payload.email_template) || '1',
    enabled: normalizeBoolean(payload.enabled)
  }
  const errors = []
  for (const [field, label] of [
    ['name', '称呼'],
    ['email', '邮箱'],
    ['locationName', '地点'],
    ['locationQuery', '查询'],
    ['timezone', '时区']
  ]) {
    if (!values[field]) errors.push(`${label}不能为空`)
  }
  if (values.email && !hasSingleAt(values.email)) errors.push('邮箱格式无效')
  if (!LANGUAGES.includes(values.language)) errors.push('报告语言无效')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

const validateDefaults = (payload = {}) => {
  const values = {
    locationName: trim(payload.location_name),
    locationQuery: trim(payload.location_query),
    timezone: trim(payload.timezone),
    language: trim(payload.language) || 'zh-CN',
    localSendTime: trim(payload.local_send_time),
    reportType: trim(payload.report_type),
    sendPolicy: trim(payload.send_policy),
    scheduleEnabled: normalizeBoolean(payload.schedule_enabled)
  }
  const errors = []
  for (const [field, label] of [
    ['locationName', '默认地点名称'],
    ['locationQuery', '默认 Provider 查询'],
    ['timezone', '默认时区'],
    ['localSendTime', '默认发送时间']
  ]) {
    if (!values[field]) errors.push(`${label}不能为空`)
  }
  if (!LANGUAGES.includes(values.language)) errors.push('默认报告语言无效')
  if (!isValidLocalTime(values.localSendTime)) errors.push('默认发送时间必须是 HH:MM 格式')
  if (!REPORT_TYPES.includes(values.reportType)) errors.push('报告类型无效')
  if (!SEND_POLICIES.includes(values.sendPolicy)) errors.push('发送策略无效')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

const validateSchedule = (payload = {}, configuration) => {
  const values = {
    id: trim(payload.schedule_id),
    recipientId: trim(payload.recipient_id),
    localSendTime: trim(payload.local_send_time),
    reportType: trim(payload.report_type),
    sendPolicy: trim(payload.send_policy),
    enabled: normalizeBoolean(payload.enabled)
  }
  const errors = []
  const recipient = configuration.recipients.find((item) => item.id === values.recipientId && !item.archivedAt)
  if (!recipient) errors.push('收件人不存在')
  if (!isValidLocalTime(values.localSendTime)) errors.push('发送时间必须是 HH:MM 格式')
  if (!REPORT_TYPES.includes(values.reportType)) errors.push('报告类型无效')
  if (!SEND_POLICIES.includes(values.sendPolicy)) errors.push('发送策略无效')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

const validateSmtp = (payload = {}) => {
  const values = {
    host: trim(payload.host),
    port: Number(trim(payload.port)),
    username: trim(payload.username),
    password: trim(payload.password),
    security: trim(payload.security),
    senderEmail: trim(payload.sender_email)
  }
  const errors = []
  if (!Number.isInteger(values.port) || values.port < 1 || values.port > 65535) errors.push('SMTP 端口必须在 1 到 65535 之间')
  if (!SMTP_SECURITY_MODES.includes(values.security)) errors.push('SMTP 安全方式无效')
  if (values.senderEmail && !hasSingleAt(values.senderEmail)) errors.push('发件邮箱格式无效')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

const validateBranding = (payload = {}) => {
  const values = {
    reportTitle: trim(payload.report_title),
    accentColor: trim(payload.accent_color),
    footerText: trim(payload.footer_text),
    greetingVisible: normalizeBoolean(payload.greeting_visible),
    dataSourceVisible: normalizeBoolean(payload.data_source_visible)
  }
  const errors = []
  if (!/^#[0-9a-fA-F]{6}$/.test(values.accentColor)) errors.push('强调色必须是 #RRGGBB 格式')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

const validateManualPreview = (payload = {}, configuration) => {
  const values = {
    recipientId: trim(payload.recipient_id),
    reportType: trim(payload.report_type)
  }
  const errors = []
  const recipient = configuration.recipients.find((item) => item.id === values.recipientId && !item.archivedAt)
  if (!recipient) errors.push('收件人不存在')
  if (!REPORT_TYPES.includes(values.reportType)) errors.push('报告类型无效')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: { ...values, recipient } }
}

const parseNonNegativeInteger = (value) => {
  const normalized = trim(value)
  if (!normalized) return null
  const number = Number(normalized)
  return Number.isInteger(number) && number >= 0 ? number : null
}

const validateNotifications = (payload = {}) => {
  const retentionDays = parseNonNegativeInteger(payload.retention_days)
  const alertCooldownMinutes = parseNonNegativeInteger(payload.alert_cooldown_minutes)
  const values = {
    adminEmail: trim(payload.admin_email),
    webhookUrl: trim(payload.webhook_url),
    retentionDays,
    alertCooldownMinutes,
    webhookEnabled: normalizeBoolean(payload.webhook_enabled),
    secretKeyBackupConfirmed: normalizeBoolean(payload.secret_key_backup_confirmed)
  }
  const errors = []
  if (values.adminEmail && !hasSingleAt(values.adminEmail)) errors.push('管理员邮箱格式无效')
  if (retentionDays === null) errors.push('历史保留天数必须是非负整数')
  if (alertCooldownMinutes === null) errors.push('告警冷却分钟必须是非负整数')
  return errors.length > 0 ? { ok: false, errors, values } : { ok: true, value: values }
}

module.exports = { normalizeBoolean, validateBranding, validateDefaults, validateManualPreview, validateNotifications, validateRecipient, validateSchedule, validateSmtp }
