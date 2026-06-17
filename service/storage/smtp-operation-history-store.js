const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const DEFAULT_SMTP_OPERATION_HISTORY_LIMIT = 50
const SMTP_OPERATION_ACTIONS = ['all', 'test-connection', 'test-email']
const SMTP_OPERATION_STATUSES = ['all', 'connected', 'sent', 'failed']
const SMTP_OPERATION_CSV_COLUMNS = ['id', 'createdAt', 'action', 'status', 'recipientId', 'recipientName', 'recipientEmail', 'messageId', 'error']

const smtpOperationHistoryPath = (paths) => path.join(paths.dataDir, 'smtp-operation-history.json')

const normalizeAllowedValue = (value, allowedValues) => {
  const normalized = String(value || 'all').trim()
  return allowedValues.includes(normalized) ? normalized : 'all'
}

const normalizeRecipientFilter = (value, allowedRecipientIds = []) => {
  const normalized = String(value || 'all').trim()
  if (normalized === 'all' || normalized.length === 0) {
    return 'all'
  }
  return allowedRecipientIds.includes(normalized) ? normalized : 'all'
}

const normalizeSmtpOperationHistoryFilters = (filters = {}, options = {}) => ({
  action: normalizeAllowedValue(filters.action, SMTP_OPERATION_ACTIONS),
  status: normalizeAllowedValue(filters.status, SMTP_OPERATION_STATUSES),
  recipientId: normalizeRecipientFilter(filters.recipientId, options.allowedRecipientIds || [])
})

const filterSmtpOperationHistory = (records, filters = {}) => records.filter((record) => {
  if (filters.action && filters.action !== 'all' && record.action !== filters.action) {
    return false
  }
  if (filters.status && filters.status !== 'all' && record.status !== filters.status) {
    return false
  }
  if (filters.recipientId && filters.recipientId !== 'all' && record.recipientId !== filters.recipientId) {
    return false
  }
  return true
})

const listSmtpOperationHistory = (paths, filters = {}, options = {}) => {
  const normalizedFilters = normalizeSmtpOperationHistoryFilters(filters, options)
  return {
    filters: normalizedFilters,
    records: filterSmtpOperationHistory(loadSmtpOperationHistory(paths), normalizedFilters)
  }
}

const escapeCsv = (value = '') => {
  const stringValue = String(value ?? '')
  return `"${stringValue.replace(/"/g, '""')}"`
}

const serializeSmtpOperationHistoryCsv = (records = []) => {
  const header = `${SMTP_OPERATION_CSV_COLUMNS.join(',')}\n`
  const rows = records.map((record) => SMTP_OPERATION_CSV_COLUMNS
    .map((column) => escapeCsv(record[column]))
    .join(','))
  return `${header}${rows.join('\n')}${rows.length > 0 ? '\n' : ''}`
}

const loadSmtpOperationHistory = (paths) => {
  const file = smtpOperationHistoryPath(paths)
  if (!existsSync(file)) return []
  const records = JSON.parse(readFileSync(file, 'utf8'))
  return Array.isArray(records) ? records : []
}

const saveSmtpOperationHistory = (paths, records) => {
  mkdirSync(paths.dataDir, { recursive: true })
  writeFileSync(smtpOperationHistoryPath(paths), `${JSON.stringify(records, null, 2)}\n`)
}

const appendSmtpOperationHistory = (paths, record, options = {}) => {
  const limit = Number.isInteger(options.limit) && options.limit > 0
    ? options.limit
    : DEFAULT_SMTP_OPERATION_HISTORY_LIMIT
  const records = loadSmtpOperationHistory(paths).concat(record).slice(-limit)
  saveSmtpOperationHistory(paths, records)
  return records
}

module.exports = {
  DEFAULT_SMTP_OPERATION_HISTORY_LIMIT,
  SMTP_OPERATION_ACTIONS,
  SMTP_OPERATION_STATUSES,
  appendSmtpOperationHistory,
  filterSmtpOperationHistory,
  listSmtpOperationHistory,
  loadSmtpOperationHistory,
  normalizeSmtpOperationHistoryFilters,
  saveSmtpOperationHistory,
  serializeSmtpOperationHistoryCsv,
  smtpOperationHistoryPath
}
